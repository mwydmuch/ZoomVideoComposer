import click
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os
import shutil
from hashlib import md5
from tqdm import trange
from math import log, ceil
import moviepy.video.io.ImageSequenceClip


def get_easing(easing):
    functions = {
        'linear': lambda x: x,
    }
    return functions[easing]


def zoom_crop(image, zoom):
    width, height = image.size
    zoom_width = width * zoom
    zoom_height = height * zoom
    zoom_image = image.resize((int(zoom_width), int(zoom_height)), Image.LANCZOS)
    return zoom_image.crop((
        (zoom_width - width) / 2,
        (zoom_height - height) / 2,
        (zoom_width + width) / 2,
        (zoom_height + height) / 2
    ))


def resize_scale(image, scale):
    width, height = image.size
    return image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)


@click.command()
@click.argument('image_paths', nargs=-1, type=click.Path(exists=True))
@click.option('-z', '--zoom-ratio', type=float, default=2.0)
@click.option('-d', '--duration', type=float, default=10.0)
@click.option('-e', '--easing', type=click.Choice(['linear', 'ease-in', 'ease-out']), default='linear')
@click.option('-r', '--direction', type=click.Choice(['in', 'out']), default='in')
@click.option('-o', '--output', type=click.Path(), default='output.mp4')
@click.option('-t', '--tmp-dir', type=click.Path(), default='tmp')
@click.option('-f', '--fps', type=int, default=30)
@click.option('-w', '--width', type=int, default=512)
@click.option('-h', '--height', type=int, default=512)
def zoom_video_composer(image_paths, zoom_ratio, duration, easing, direction, output, tmp_dir='tmp', fps=30, width=512, height=512):
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
        click.echo(f"Reading and processing image file: {image_path}")
        image = Image.open(image_path)
        images.append(image)

    # Setup some variables
    easing_func = get_easing(easing)
    num_images = len(image_paths) - 1
    num_frames = int(duration * fps)
    end_zoom = zoom_ratio ** num_images
    end_zoom_sum = zoom_ratio * num_images
    tmp_dir_hash = os.path.join(tmp_dir, md5(''.join(image_paths).encode('utf-8')).hexdigest())

    # Create tmp dir
    if not os.path.exists(tmp_dir_hash):
        click.echo(f"Creating temporary directory for frames: {tmp_dir}")
        os.makedirs(tmp_dir_hash, exist_ok=True)

    # Create frames
    for i in trange(num_frames):
        current_zoom = zoom_ratio ** ((easing_func(i / (num_frames - 1))) * num_images)
        zoom_log = log(current_zoom, zoom_ratio)
        local_zoom = zoom_ratio ** (zoom_log % 1)
        current_image_idx = ceil(log(current_zoom, zoom_ratio))
        print(f"CZ: {current_zoom}, ZL: {zoom_log}, LZ: {local_zoom}, IMG: {current_image_idx}")

        if i == 0:
            frame = images[0]
        else:
            inner_image = images[current_image_idx]
            outer_image = images[current_image_idx - 1]

            inner_image = resize_scale(inner_image, local_zoom / zoom_ratio)
            frame = zoom_crop(outer_image, local_zoom)
            frame.paste(inner_image, (int((outer_image.width - inner_image.width) / 2), int((outer_image.height - inner_image.height) / 2)))
        
        frame = frame.resize((width, height), Image.LANCZOS)
        frame_path = os.path.join(tmp_dir_hash, f'{i}.png')
        frame.save(frame_path)
        
    # Write video
    click.echo(f"Writing video to: {output}")
    image_files = [os.path.join(tmp_dir_hash, f'{x}.png') for x in range(num_frames)]
    clip = moviepy.video.io.ImageSequenceClip.ImageSequenceClip(image_files, fps=fps)
    clip.write_videofile(output)

    # Remove tmp dir
    shutil.rmtree(tmp_dir_hash, ignore_errors=False, onerror=None)
    if not os.listdir(tmp_dir):
        click.echo(f"Removing empty temporary directory for frames: {tmp_dir}")
        os.rmdir(tmp_dir)
    

if __name__ == '__main__':
    zoom_video_composer()
