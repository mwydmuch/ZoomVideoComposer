import click
from PIL import Image
import numpy as np
import os
import shutil
from hashlib import md5
from multiprocessing import cpu_count
from joblib import Parallel, delayed
from tqdm import trange
from math import log, ceil
import moviepy.video.io.ImageSequenceClip


EASING_FUNCTIONS = {
    "linear": lambda x: x,
}
DEFAULT_EASING_KEY = "linear"
DEFAULT_EASING_FUNCTION = EASING_FUNCTIONS[DEFAULT_EASING_KEY]

RESAMPLING_FUNCTIONS = {
    "nearest": Image.Resampling.NEAREST,
    "box": Image.Resampling.BOX,
    "bilinear": Image.Resampling.BILINEAR,
    "hamming": Image.Resampling.HAMMING,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}
DEFAULT_RESAMPLING_KEY = "lanczos"
DEFAULT_RESAMPLING_FUNCTION = RESAMPLING_FUNCTIONS[DEFAULT_RESAMPLING_KEY]  


def zoom_crop(image, zoom, resampling_func=Image.Resampling.LANCZOS):
    width, height = image.size
    zoom_width = width * zoom
    zoom_height = height * zoom
    zoom_image = image.resize((int(zoom_width), int(zoom_height)), resampling_func)
    return zoom_image.crop(
        (
            (zoom_width - width) / 2,
            (zoom_height - height) / 2,
            (zoom_width + width) / 2,
            (zoom_height + height) / 2,
        )
    )


def resize_scale(image, scale, resampling_func=Image.Resampling.LANCZOS):
    width, height = image.size
    return image.resize((int(width * scale), int(height * scale)), resampling_func)


def zoom_in(zoom, easing_func, i, num_frames, num_images):
    return zoom ** ((easing_func(i / (num_frames - 1))) * num_images)


def zoom_out(zoom, easing_func, i, num_frames, num_images):
    return zoom ** ((1 - easing_func(i / (num_frames - 1))) * num_images)


@click.command()
@click.argument("image_paths", nargs=-1, type=click.Path(exists=True))
@click.option("-z", "--zoom", type=float, default=2.0)
@click.option("-d", "--duration", type=float, default=10.0)
@click.option(
    "-e", "--easing", type=click.Choice(list(EASING_FUNCTIONS.keys())), default=DEFAULT_EASING_KEY
)
@click.option("-r", "--direction", type=click.Choice(["in", "out", "inout", "outin"]), default="out")
@click.option("-o", "--output", type=click.Path(), default="output.mp4")
@click.option("-t", "threads", type=int, default=-1)
@click.option("--tmp-dir", type=click.Path(), default="tmp")
@click.option("-f", "--fps", type=int, default=30)
@click.option("-w", "--width", type=int, default=512)
@click.option("-h", "--height", type=int, default=512)
@click.option(
    "-s",
    "--resampling",
    type=click.Choice(list(RESAMPLING_FUNCTIONS.keys())),
    default=DEFAULT_RESAMPLING_KEY,
)
@click.option("--keep-tmp", is_flag=True, default=True)
@click.option("-m", "--margin", type=int, default=50)
def zoom_video_composer(
    image_paths,
    zoom=2.0,
    duration=10.0,
    easing=DEFAULT_EASING_KEY,
    direction="in",
    output="output.mp4",
    threads=-1,
    tmp_dir="tmp",
    fps=30,
    width=512,
    height=512,
    resampling=DEFAULT_RESAMPLING_KEY,
    keep_tmp=True,
    margin=50,
):
    """Compose a zoom video from multiple video files."""

    # Read images
    _image_paths = []
    for image_path in image_paths:
        if os.path.isfile(image_path):
            _image_paths.append(image_path)
        elif os.path.isdir(image_path):
            for subimage_path in sorted(os.listdir(image_path)):
                _image_paths.append(os.path.join(image_path, subimage_path))
    image_paths = _image_paths

    images = []
    for image_path in image_paths:
        if not image_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            click.echo(f"Unsupported file type: {image_path}, skipping")
            continue
        click.echo(f"Reading image file: {image_path}")
        image = Image.open(image_path)
        images.append(image)

    # Setup some variables
    easing_func = EASING_FUNCTIONS.get(easing, None)
    if easing_func is None:
        raise ValueError(f"Unsupported easing function: {easing}")
    
    resampling_func = RESAMPLING_FUNCTIONS.get(resampling, None)
    if resampling_func is None:
        raise ValueError(f"Unsupported resampling function: {resampling}")
    
    num_images = len(images) - 1
    num_frames = int(duration * fps)
    num_frames_half = int(num_frames / 2)
    tmp_dir_hash = os.path.join(
        tmp_dir, md5("".join(image_paths).encode("utf-8")).hexdigest()
    )

    # Create tmp dir
    if not os.path.exists(tmp_dir_hash):
        click.echo(f"Creating temporary directory for frames: {tmp_dir}")
        os.makedirs(tmp_dir_hash, exist_ok=True)

    if direction in ["out", "outin"]:
        images.reverse()

    # Blend margins
    for i in range(1, num_images + 1):
        inner_image = images[i]
        outer_image = images[i - 1]
        inner_image = inner_image.crop((margin, margin, inner_image.width - margin, inner_image.height - margin))
        image = zoom_crop(outer_image, zoom, resampling_func)
        image.paste(inner_image, (margin, margin))
        images[i] = image

    # Create frames
    def process_frame(i):  # to improve
        if direction == "in":
            current_zoom = zoom_in(zoom, easing_func, i, num_frames, num_images)
        elif direction == "out":
            current_zoom = zoom_out(zoom, easing_func, i, num_frames, num_images)
        elif direction == "inout":
            if i < num_frames_half:
                current_zoom = zoom_in(zoom, easing_func, i, num_frames_half, num_images)
            else:
                current_zoom = zoom_out(zoom, easing_func, i - num_frames_half, num_frames_half, num_images)
        elif direction == "outin":
            if i < num_frames_half:
                current_zoom = zoom_out(zoom, easing_func, i, num_frames_half, num_images)
            else:
                current_zoom = zoom_in(zoom, easing_func, i - num_frames_half, num_frames_half, num_images)
        else:
            raise ValueError(f"Unsupported direction: {direction}")
        
        current_zoom_log = log(current_zoom, zoom)
        local_zoom = zoom ** (current_zoom_log % 1)
        current_image_idx = ceil(log(current_zoom, zoom))

        if local_zoom == 1.0:
            frame = images[current_image_idx]
        else:
            inner_image = images[current_image_idx]
            outer_image = images[current_image_idx - 1]

            inner_image = resize_scale(
                inner_image, local_zoom / zoom, resampling_func
            )
            frame = zoom_crop(outer_image, local_zoom, resampling_func)
            frame.paste(
                inner_image,
                (
                    int((outer_image.width - inner_image.width) / 2),
                    int((outer_image.height - inner_image.height) / 2),
                ),
            )

        frame = frame.resize((width, height), resampling_func)
        frame_path = os.path.join(tmp_dir_hash, f"{i}.png")
        frame.save(frame_path)

    n_jobs = threads if threads > 0 else cpu_count() - threads
    Parallel(n_jobs=n_jobs)(delayed(process_frame)(i) for i in trange(num_frames))

    # Write video
    click.echo(f"Writing video to: {output}")
    image_files = [os.path.join(tmp_dir_hash, f"{x}.png") for x in range(num_frames)]
    clip = moviepy.video.io.ImageSequenceClip.ImageSequenceClip(image_files, fps=fps)
    clip.write_videofile(output)

    # Remove tmp dir
    if not keep_tmp:
        shutil.rmtree(tmp_dir_hash, ignore_errors=False, onerror=None)
        if not os.listdir(tmp_dir):
            click.echo(f"Removing empty temporary directory for frames: {tmp_dir}")
            os.rmdir(tmp_dir)


if __name__ == "__main__":
    zoom_video_composer()
