#!/usr/bin/env python3

# zoom_video_composer.py v0.2.3
# https://github.com/mwydmuch/ZoomVideoComposer

# Copyright (c) 2023 Marek Wydmuch and the respective contributors

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import click
from PIL import Image
import os
import shutil
from hashlib import md5
from multiprocessing import cpu_count
from joblib import Parallel, delayed
from tqdm import trange
from math import log, ceil, pow, sin, cos, pi
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.editor import VideoFileClip, AudioFileClip
from concurrent.futures import ThreadPoolExecutor
import concurrent
from tqdm import tqdm


EASING_FUNCTIONS = {
    "linear": lambda x: x,
    "easeInSine": lambda x: 1 - cos((x * pi) / 2),
    "easeOutSine": lambda x: sin((x * pi) / 2),
    "easeInOutSine": lambda x: -(cos(pi * x) - 1) / 2,
    "easeInQuad": lambda x: x * x,
    "easeOutQuad": lambda x: 1 - (1 - x) * (1 - x),
    "easeInOutQuad": lambda x: 2 * x * x if x < 0.5 else 1 - pow(-2 * x + 2, 2) / 2,
    "easeInCubic": lambda x: x * x * x,
    "easeOutCubic": lambda x: 1 - pow(1 - x, 3),
    "easeInOutCubic": lambda x: 4 * x * x * x
    if x < 0.5
    else 1 - pow(-2 * x + 2, 3) / 2,
}
DEFAULT_EASING_KEY = "easeInOutSine"
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
    zoom_size = (int(width * zoom), int(height * zoom))
    crop_box = (
        (zoom_size[0] - width) / 2,
        (zoom_size[1] - height) / 2,
        (zoom_size[0] + width) / 2,
        (zoom_size[1] + height) / 2,
    )
    return image.resize(zoom_size, resampling_func).crop(crop_box)


def resize_scale(image, scale, resampling_func=Image.Resampling.LANCZOS):
    width, height = image.size
    return image.resize((int(width * scale), int(height * scale)), resampling_func)


def zoom_in_log(easing_func, i, num_frames, num_images):
    return (easing_func(i / (num_frames - 1))) * num_images


def zoom_out_log(easing_func, i, num_frames, num_images):
    return (1 - easing_func(i / (num_frames - 1))) * num_images


def zoom_in(zoom, easing_func, i, num_frames, num_images):
    return zoom ** zoom_in_log(easing_func, i, num_frames, num_images)


def zoom_out(zoom, easing_func, i, num_frames, num_images):
    return zoom ** zoom_out_log(easing_func, i, num_frames, num_images)


def get_px_or_fraction(value, reference_value):
    if value <= 1:
        value = reference_value * value
    return int(value)


@click.command()
@click.argument(
    "image_paths",
    nargs=-1,
    type=click.Path(exists=True),
    required=True,
)
@click.option(
    "-a",
    "--audio_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Audio file path that will be added to the video.",
)
@click.option(
    "-z",
    "--zoom",
    type=float,
    default=2.0,
    help="Zoom factor/ratio between images.",
    show_default=True,
)
@click.option(
    "-d",
    "--duration",
    type=float,
    default=10.0,
    help="Duration of the video in seconds.",
    show_default=True,
)
@click.option(
    "-e",
    "--easing",
    type=click.Choice(list(EASING_FUNCTIONS.keys())),
    default=DEFAULT_EASING_KEY,
    help="Easing function.",
    show_default=True,
)
@click.option(
    "-r",
    "--direction",
    type=click.Choice(["in", "out", "inout", "outin"]),
    default="out",
    help="Zoom direction. Inout and outin combine both directions.",
    show_default=True,
)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    default="output.mp4",
    help="Output video file.",
    show_default=True,
)
@click.option(
    "-t",
    "--threads",
    type=int,
    default=-1,
    help="Number of threads to use to generate frames. Use values <= 0 for number of available threads on your machine minus the provided absolute value.",
    show_default=True,
)
@click.option(
    "--tmp-dir",
    type=click.Path(),
    default="tmp",
    help="Temporary directory to store frames.",
    show_default=True,
)
@click.option(
    "-f",
    "--fps",
    type=int,
    default=30,
    help="Frames per second of the output video.",
    show_default=True,
)
@click.option(
    "-w",
    "--width",
    type=float,
    default=1,
    help="Width of the output video. Values > 1 are interpreted as specific sizes in pixels. Values <= 1 are interpreted as a fraction of the width of the first image.",
    show_default=True,
)
@click.option(
    "-h",
    "--height",
    type=float,
    default=1,
    help="Height of the output video. Values > 1 are interpreted as specific sizes in pixels. Values <= 1 are interpreted as a fraction of the height of the first image.",
    show_default=True,
)
@click.option(
    "-s",
    "--resampling",
    type=click.Choice(list(RESAMPLING_FUNCTIONS.keys())),
    default=DEFAULT_RESAMPLING_KEY,
    help="Resampling techique to use when resizing images.",
    show_default=True,
)
@click.option(
    "-m",
    "--margin",
    type=float,
    default=0.05,
    help="Size of the margin to cut from the edges of each image for better blending with the next/previous image. Values > 1 are interpreted as specific sizes in pixels. Values <= 1 are interpreted as a fraction of the smaller size of the first image.",
    show_default=True,
)
@click.option(
    "--keep-frames",
    is_flag=True,
    default=False,
    help="Keep frames in the temporary directory. Otherwise, it will be deleted after the video is generated.",
    show_default=True,
)
@click.option(
    "--skip-video-generation",
    is_flag=True,
    default=False,
    help="Skip video generation. Useful if you only want to generate the frames. This option will keep the temporary directory similar to --keep-frames flag.",
    show_default=True,
)
@click.option(
    "--reverse-images",
    is_flag=True,
    default=False,
    help="Reverse the order of the images.",
    show_default=True,
)
def zoom_video_composer(
    image_paths,
    audio_path=None,
    zoom=2.0,
    duration=10.0,
    easing=DEFAULT_EASING_KEY,
    direction="out",
    output="output.mp4",
    threads=-1,
    tmp_dir="tmp",
    fps=30,
    width=1,
    height=1,
    resampling=DEFAULT_RESAMPLING_KEY,
    margin=0.05,
    keep_frames=False,
    skip_video_generation=False,
    reverse_images=False,
):
    """Compose a zoom video from multiple provided images."""

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
    click.echo(f"Reading {len(image_paths)} image files ...")
    for image_path in image_paths:
        if not image_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            click.echo(f"Unsupported file type: {image_path}, skipping")
            continue

        image = Image.open(image_path)
        images.append(image)

    if len(images) < 2:
        raise ValueError("At least two images are required to create a zoom video")

    # Setup some additional variables
    easing_func = EASING_FUNCTIONS.get(easing, None)
    if easing_func is None:
        raise ValueError(f"Unsupported easing function: {easing}")

    resampling_func = RESAMPLING_FUNCTIONS.get(resampling, None)
    if resampling_func is None:
        raise ValueError(f"Unsupported resampling function: {resampling}")

    num_images = len(images) - 1
    num_frames = int(duration * fps)
    num_frames_half = int(num_frames / 2)
    print(image_paths)
    tmp_dir_hash = os.path.join(
        tmp_dir, md5("".join(image_paths).encode("utf-8")).hexdigest()
    )
    print(tmp_dir_hash)

    width = get_px_or_fraction(width, images[0].width)
    height = get_px_or_fraction(height, images[0].height)
    margin = get_px_or_fraction(margin, min(images[0].width, images[0].height))

    # Create tmp dir
    if not os.path.exists(tmp_dir_hash):
        click.echo(f"Creating temporary directory for frames: {tmp_dir_hash} ...")
        os.makedirs(tmp_dir_hash, exist_ok=True)

    if direction in ["out", "outin"]:
        images.reverse()

    if reverse_images:
        images.reverse()

    # Blend images (take care of margins)
    click.echo(f"Blending {len(images)} images ...")
    for i in trange(1, num_images + 1):
        inner_image = images[i]
        outer_image = images[i - 1]
        inner_image = inner_image.crop(
            (margin, margin, inner_image.width - margin, inner_image.height - margin)
        )

        # Some coloring for debugging purposes
        # debug_colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta']
        # layer = Image.new('RGB', inner_image.size, debug_colors[i % 6])
        # inner_image = Image.blend(inner_image, layer, 0.25)

        image = zoom_crop(outer_image, zoom, resampling_func)
        image.paste(inner_image, (margin, margin))
        images[i] = image

        # Save image for debugging purposes
        # image_path = os.path.join(tmp_dir_hash, f"_blending_step_1_{i:06d}.png")
        # image.save(image_path)

    images_resized = [resize_scale(i, zoom, resampling_func) for i in images]
    for i in trange(num_images, 0, -1):
        inner_image = images_resized[i]
        image = images_resized[i - 1]
        inner_image = resize_scale(inner_image, 1.0 / zoom, resampling_func)

        # Some coloring for debugging purposes
        # debug_colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta']
        # layer = Image.new('RGB', inner_image.size, debug_colors[i % 6])
        # inner_image = Image.blend(inner_image, layer, 0.25)

        image.paste(
            inner_image,
            (
                int((image.width - inner_image.width) / 2),
                int((image.height - inner_image.height) / 2),
            ),
        )
        images_resized[i] = image

        # Save image for debugging purposes
        # image_path = os.path.join(tmp_dir_hash, f"_blending_step_2_{i:06d}.png")
        # image.save(image_path)

    images = images_resized

    # Create frames
    def process_frame(i):  # to improve
        if direction == "in":
            current_zoom_log = zoom_in_log(easing_func, i, num_frames, num_images)
        elif direction == "out":
            current_zoom_log = zoom_out_log(easing_func, i, num_frames, num_images)
        elif direction == "inout":
            if i < num_frames_half:
                current_zoom_log = zoom_in_log(
                    easing_func, i, num_frames_half, num_images
                )
            else:
                current_zoom_log = zoom_out_log(
                    easing_func, i - num_frames_half, num_frames_half, num_images
                )
        elif direction == "outin":
            if i < num_frames_half:
                current_zoom_log = zoom_out_log(
                    easing_func, i, num_frames_half, num_images
                )
            else:
                current_zoom_log = zoom_in_log(
                    easing_func, i - num_frames_half, num_frames_half, num_images
                )
        else:
            raise ValueError(f"Unsupported direction: {direction}")

        current_image_idx = ceil(current_zoom_log)
        local_zoom = zoom ** (current_zoom_log - current_image_idx + 1)
        #print(current_zoom_log, current_image_idx, local_zoom, zoom ** current_zoom_log)

        if current_zoom_log == 0.0:
            frame = images[0]
        else:
            frame = images[current_image_idx]
            frame = zoom_crop(frame, local_zoom, resampling_func)

        frame = frame.resize((width, height), resampling_func)
        frame_path = os.path.join(tmp_dir_hash, f"{i:06d}.png")
        frame.save(frame_path)

    n_jobs = threads if threads > 0 else cpu_count() - threads
    click.echo(f"Creating frames in {n_jobs} threads ...")

    with ThreadPoolExecutor(max_workers=n_jobs) as executor:
        futures = [executor.submit(process_frame, i) for i in range(num_frames)]
        try:
            for _ in tqdm(concurrent.futures.as_completed(futures), total=num_frames):
                pass
        except KeyboardInterrupt:
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    # Write video
    click.echo(f"Writing video to: {output} ...")
    image_files = [
        os.path.join(tmp_dir_hash, f"{i:06d}.png") for i in range(num_frames)
    ]
    video_clip = ImageSequenceClip(image_files, fps=fps)
    video_write_kwargs = {"codec": "libx264"}

    # Add audio
    if audio_path:
        click.echo(f"Adding audio from: {audio_path} ...")
        audio_clip = AudioFileClip(audio_path)
        audio_clip = audio_clip.subclip(0, video_clip.end)
        video_clip = video_clip.set_audio(audio_clip)
        video_write_kwargs["audio_codec"] = "aac"

    video_clip.write_videofile(output, **video_write_kwargs)

    # Remove tmp dir
    if not keep_frames and not skip_video_generation:
        shutil.rmtree(tmp_dir_hash, ignore_errors=False, onerror=None)
        if not os.listdir(tmp_dir):
            click.echo(f"Removing empty temporary directory for frames: {tmp_dir} ...")
            os.rmdir(tmp_dir)

    click.echo("Done!")


if __name__ == "__main__":
    zoom_video_composer()
