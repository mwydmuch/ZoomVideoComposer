#!/usr/bin/env python3

# zoom_video_composer.py v0.3.0
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

VERSION = "0.3.0"
import concurrent
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from hashlib import md5
from multiprocessing import cpu_count
import click
from tqdm import tqdm

from helpers import *


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
    "--easing-power",
    type=float,
    default=DEFAULT_EASING_POWER,
    help="Power argument of easeInPow, easeOutPow and easeInOutPow easing functions.",
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
    help="Width of the output video. Values > 1 are interpreted as specific sizes in pixels. Values <= 1 are "
    "interpreted as a fraction of the width of the first image.",
    show_default=True,
)
@click.option(
    "-h",
    "--height",
    type=float,
    default=1,
    help="Height of the output video. Values > 1 are interpreted as specific sizes in pixels. Values <= 1 are "
    "interpreted as a fraction of the height of the first image.",
    show_default=True,
)
@click.option(
    "-s",
    "--resampling",
    type=click.Choice(list(RESAMPLING_FUNCTIONS_PIL.keys())),
    default=DEFAULT_RESAMPLING_KEY,
    help="Resampling technique to use when resizing images.",
    show_default=True,
)
@click.option(
    "-m",
    "--margin",
    type=float,
    default=0.05,
    help="Size of the margin to cut from the edges of each image for better blending with the next/previous image. "
    "Values > 1 are interpreted as specific sizes in pixels. Values <= 1 are interpreted as a fraction of the "
    "smaller size of the first image.",
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
    help="Number of threads to use to generate frames. Use values <= 0 for number of available threads on your "
    "machine minus the provided absolute value.",
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
    help="Skip video generation. Useful if you only want to generate the frames. This option will keep the temporary "
    "directory similar to --keep-frames flag.",
    show_default=True,
)
@click.option(
    "--reverse-images",
    is_flag=True,
    default=False,
    help="Reverse the order of the images.",
    show_default=True,
)
@click.option(
    "--image-engine",
    type=click.Choice(list(IMAGE_CLASSES.keys())),
    default=DEFAULT_IMAGE_ENGINE,
    help="Image engine to use for image processing.",
    show_default=True,
)
def zoom_video_composer_cli(
    image_paths,
    audio_path=None,
    zoom=2.0,
    duration=10.0,
    easing=DEFAULT_EASING_KEY,
    easing_power=DEFAULT_EASING_POWER,
    direction="out",
    fps=30,
    reverse_images=False,
    width=1,
    height=1,
    resampling=DEFAULT_RESAMPLING_KEY,
    margin=0.05,
    output="output.mp4",
    threads=-1,
    tmp_dir="tmp",
    keep_frames=False,
    skip_video_generation=False,
    image_engine=DEFAULT_IMAGE_ENGINE,
):
    """Compose a zoom video from multiple provided images."""
    zoom_video_composer(
        image_paths,
        audio_path,
        zoom,
        duration,
        easing,
        easing_power,
        direction,
        fps,
        reverse_images,
        width,
        height,
        resampling,
        margin,
        output,
        threads,
        tmp_dir,
        keep_frames,
        skip_video_generation,
        image_engine,
    )


def zoom_video_composer(
    image_paths,
    audio_path=None,
    zoom=2.0,
    duration=10.0,
    easing=DEFAULT_EASING_KEY,
    easing_power=DEFAULT_EASING_POWER,
    direction="out",
    fps=30,
    reverse_images=False,
    width=1,
    height=1,
    resampling=DEFAULT_RESAMPLING_KEY,
    margin=0.05,
    output="output.mp4",
    threads=-1,
    tmp_dir="tmp",
    keep_frames=False,
    skip_video_generation=False,
    image_engine=DEFAULT_IMAGE_ENGINE,
    logger=click.echo,
):
    """Compose a zoom video from multiple provided images."""
    # Read images
    image_paths = get_image_paths(image_paths)
    logger(f"Reading {len(image_paths)} image files ...")
    images = read_images(image_paths, logger, image_engine)

    # Setup some additional variables
    easing_func = get_easing_function(easing, easing_power)
    resampling_func = get_resampling_function(resampling, image_engine)

    num_images = len(images) - 1
    num_frames = int(duration * fps)
    num_frames_half = int(num_frames / 2)
    tmp_dir_hash = os.path.join(
        tmp_dir, md5("".join(image_paths).encode("utf-8")).hexdigest()
    )

    # Calculate sizes based on arguments
    width, height, margin = get_sizes(images[0], width, height, margin)

    # Create tmp dir
    if not os.path.exists(tmp_dir_hash):
        logger(f"Creating temporary directory for frames: {tmp_dir_hash} ...")
        os.makedirs(tmp_dir_hash, exist_ok=True)

    # Reverse images
    images = images_reverse(images, direction, reverse_images)

    # Blend images (take care of margins)
    logger(f"Blending {len(images)} images ...")
    images = blend_images(images, margin, zoom, resampling_func)

    # Create frames
    n_jobs = threads if threads > 0 else cpu_count() - threads
    logger(f"Creating frames in {n_jobs} threads ...")

    with ThreadPoolExecutor(max_workers=n_jobs) as executor:
        futures = [
            executor.submit(
                process_frame,
                i,
                images,
                direction,
                easing_func,
                num_frames,
                num_frames_half,
                num_images,
                zoom,
                width,
                height,
                resampling_func,
                tmp_dir_hash,
            )
            for i in range(num_frames)
        ]
        try:
            completed = concurrent.futures.as_completed(futures)
            for _ in tqdm(range(num_frames), desc="Generating the frames"):
                completed.__next__()
        except KeyboardInterrupt:
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    # Create video clip using images in tmp dir and audio if provided
    logger(f"Writing video to: {output} ...")
    create_video_clip(output, fps, num_frames, tmp_dir_hash, audio_path, n_jobs)

    # Remove tmp dir
    if not keep_frames and not skip_video_generation:
        shutil.rmtree(tmp_dir_hash, ignore_errors=False, onerror=None)
        if not os.listdir(tmp_dir):
            os.rmdir(tmp_dir)

    logger("Done!")
    return output


if __name__ == "__main__":
    zoom_video_composer_cli()
