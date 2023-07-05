#!/usr/bin/env python3

# zoom_video_composer.py v0.2.1
# https://github.com/mwydmuch/ZoomVideoComposer

# Copyright (c) 2023 Marek Wydmuch

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


import os
import shutil
from hashlib import md5
from math import ceil, pow, sin, cos, pi

import gradio as gr
from PIL import Image
from moviepy.editor import AudioFileClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

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


def zoom_video_composer(
        image_paths,
        audio_path,
        zoom,
        duration,
        easing,
        direction,
        fps,
        resampling,
        reverse_images,
        progress=gr.Progress()
):
    """Compose a zoom video from multiple provided images."""
    output = "output.mp4"
    threads = -1
    tmp_dir = "tmp"
    width = 1
    height = 1
    margin = 0.05
    keep_frames = False
    skip_video_generation = False

    # Read images from image_paths

    images = list(Image.open(image_path.name) for image_path in image_paths)

    if len(images) < 2:
        raise gr.Error("At least two images are required to create a zoom video")
        # raise ValueError("At least two images are required to create a zoom video")

    # gr.Info("Images loaded")
    progress(0, desc="Images loaded")

    # Setup some additional variables
    easing_func = EASING_FUNCTIONS.get(easing, None)
    if easing_func is None:
        raise gr.Error(f"Unsupported easing function: {easing}")
        # raise ValueError(f"Unsupported easing function: {easing}")

    resampling_func = RESAMPLING_FUNCTIONS.get(resampling, None)
    if resampling_func is None:
        raise gr.Error(f"Unsupported resampling function: {resampling}")
        # raise ValueError(f"Unsupported resampling function: {resampling}")

    num_images = len(images) - 1
    num_frames = int(duration * fps)
    num_frames_half = int(num_frames / 2)
    tmp_dir_hash = os.path.join(tmp_dir, md5(output.encode("utf-8")).hexdigest())
    width = get_px_or_fraction(width, images[0].width)
    height = get_px_or_fraction(height, images[0].height)
    margin = get_px_or_fraction(margin, min(images[0].width, images[0].height))

    # Create tmp dir
    if not os.path.exists(tmp_dir_hash):
        progress(0, desc="Creating temporary directory for frames")
        os.makedirs(tmp_dir_hash, exist_ok=True)

    if direction in ["out", "outin"]:
        images.reverse()

    if reverse_images:
        images.reverse()

    # Blend images (take care of margins)
    progress(0, desc=f"Blending {len(images)} images")
    for i in progress.tqdm(range(1, num_images + 1), desc="Blending images"):
        inner_image = images[i]
        outer_image = images[i - 1]
        inner_image = inner_image.crop(
            (margin, margin, inner_image.width - margin, inner_image.height - margin)
        )

        image = zoom_crop(outer_image, zoom, resampling_func)
        image.paste(inner_image, (margin, margin))
        images[i] = image

    images_resized = [resize_scale(i, zoom, resampling_func) for i in images]
    for i in progress.tqdm(range(num_images, 0, -1), desc="Resizing images"):
        inner_image = images_resized[i]
        image = images_resized[i - 1]
        inner_image = resize_scale(inner_image, 1.0 / zoom, resampling_func)

        image.paste(
            inner_image,
            (
                int((image.width - inner_image.width) / 2),
                int((image.height - inner_image.height) / 2),
            ),
        )
        images_resized[i] = image

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

        if current_zoom_log == 0.0:
            frame = images[0]
        else:
            frame = images[current_image_idx]
            frame = zoom_crop(frame, local_zoom, resampling_func)

        frame = frame.resize((width, height), resampling_func)
        frame_path = os.path.join(tmp_dir_hash, f"{i:06d}.png")
        frame.save(frame_path)

    progress(0, desc=f"Creating {num_frames} frames")
    for i in progress.tqdm(range(num_frames), desc="Creating frames"):
        process_frame(i)

    # Write video
    progress(0, desc=f"Writing video to: {output}")
    image_files = [
        os.path.join(tmp_dir_hash, f"{i:06d}.png") for i in range(num_frames)
    ]
    video_clip = ImageSequenceClip(image_files, fps=fps)
    video_write_kwargs = {"codec": "libx264"}

    # Add audio
    if audio_path:
        # audio file name
        progress(0, desc=f"Adding audio from: {os.path.basename(audio_path.name)}")
        audio_clip = AudioFileClip(audio_path.name)
        audio_clip = audio_clip.subclip(0, video_clip.end)
        video_clip = video_clip.set_audio(audio_clip)
        video_write_kwargs["audio_codec"] = "aac"

    video_clip.write_videofile(output, **video_write_kwargs)

    # Remove tmp dir
    if not keep_frames and not skip_video_generation:
        shutil.rmtree(tmp_dir_hash, ignore_errors=False, onerror=None)
        if not os.listdir(tmp_dir):
            progress(0, desc=f"Removing empty temporary directory for frames: {tmp_dir} ...")
            os.rmdir(tmp_dir)
    return output


grInputs = [
    gr.File(file_count="multiple", label="Upload images as folder", file_types=["image"]),
    gr.File(file_count="single", label="Upload audio", file_types=["audio"]),
    gr.inputs.Slider(label="Zoom factor/ratio between images", minimum=1.0, maximum=5.0, step=0.1, default=2.0),
    gr.inputs.Slider(label="Duration of the video in seconds", minimum=1.0, maximum=60.0, step=1.0, default=10.0),
    gr.inputs.Dropdown(label="Easing function used for zooming",
                       choices=["linear", "easeInSine", "easeOutSine", "easeInOutSine", "easeInQuad", "easeOutQuad",
                                "easeInOutQuad", "easeInCubic", "easeOutCubic", "easeInOutCubic"],
                       default="easeInOutSine"),
    gr.inputs.Dropdown(label="Zoom direction. Inout and outin combine both directions",
                       choices=["in", "out", "inout", "outin"], default="out"),
    gr.inputs.Slider(label="Frames per second of the output video", minimum=1, maximum=60, step=1, default=30),
    gr.inputs.Dropdown(label="Resampling technique used for resizing images",
                       choices=["nearest", "box", "bilinear", "hamming", "bicubic", "lanczos"], default="lanczos"),
    gr.inputs.Checkbox(label="Reverse images", default=False)
]

iface = gr.Interface(
    fn=zoom_video_composer,
    inputs=grInputs,
    outputs=[gr.outputs.Video(label="Video")],
    title="Zoom Video Composer",
    description="Compose a zoom video from multiple provided images.",
    allow_flagging=False,
    allow_screenshot=True,
    allow_embedding=True,
    allow_download=True)

iface.queue(concurrency_count=10).launch()
