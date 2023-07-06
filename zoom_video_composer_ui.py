#!/usr/bin/env python3

# zoom_video_composer.py v0.2.1
# https://github.com/mwydmuch/ZoomVideoComposer
# https://github.com/miwaniza/ZoomVideoComposer

# Copyright (c) 2023 Marek Wydmuch, Dmytro Yemelianov

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
from concurrent.futures import ThreadPoolExecutor
from hashlib import md5
from math import ceil, pow, sin, cos, pi

import cv2
import gradio as gr
from moviepy.editor import AudioFileClip, VideoFileClip

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


def zoom_crop_cv2(image, zoom):
    height, width, channels = image.shape
    zoom_size = (int(width * zoom), int(height * zoom))
    # crop box as integers
    crop_box = (
        int((zoom_size[0] - width) / 2),
        int((zoom_size[1] - height) / 2),
        int((zoom_size[0] + width) / 2),
        int((zoom_size[1] + height) / 2),
    )
    im = cv2.resize(image, zoom_size, interpolation=cv2.INTER_LANCZOS4)
    im = im[crop_box[1]:crop_box[3], crop_box[0]:crop_box[2]]
    return im


def resize_scale(image, scale):
    height, width = image.shape[:2]
    return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_LANCZOS4)


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
        reverse_images,
        progress=gr.Progress()
):
    """Compose a zoom video from multiple provided images."""
    output = "output.mp4"
    tmp_dir = "tmp"
    width = 1
    height = 1
    margin = 0.05
    keep_frames = False
    skip_video_generation = False

    # Read images from image_paths
    images_cv2 = list(cv2.imread(image_path.name) for image_path in image_paths)

    if len(images_cv2) < 2:
        raise gr.Error("At least two images are required to create a zoom video")

    progress(0, desc="Images loaded")

    # Setup some additional variables
    easing_func = EASING_FUNCTIONS.get(easing, None)
    if easing_func is None:
        raise gr.Error(f"Unsupported easing function: {easing}")

    num_images = len(images_cv2) - 1
    num_frames = int(duration * fps)
    num_frames_half = int(num_frames / 2)
    tmp_dir_hash = os.path.join(tmp_dir, md5(output.encode("utf-8")).hexdigest())
    width = get_px_or_fraction(width, images_cv2[0].shape[1])
    height = get_px_or_fraction(height, images_cv2[0].shape[0])
    margin = get_px_or_fraction(margin, min(images_cv2[0].shape[1], images_cv2[0].shape[0]))

    # Create tmp dir
    if not os.path.exists(tmp_dir_hash):
        progress(0, desc="Creating temporary directory for frames")
        os.makedirs(tmp_dir_hash, exist_ok=True)

    if direction in ["out", "outin"]:
        images_cv2.reverse()

    if reverse_images:
        images_cv2.reverse()

    # Blend images (take care of margins)
    progress(0, desc=f"Blending {len(images_cv2)} images")
    for i in progress.tqdm(range(1, num_images + 1), desc="Blending images"):
        inner_image = images_cv2[i]
        outer_image = images_cv2[i - 1]
        inner_image = inner_image[
                      margin:inner_image.shape[0] - margin,
                      margin:inner_image.shape[1] - margin
                      ]
        image = zoom_crop_cv2(outer_image, zoom)
        image[
        margin:margin + inner_image.shape[0],
        margin:margin + inner_image.shape[1]
        ] = inner_image
        images_cv2[i] = image

    images_resized = [resize_scale(i, zoom) for i in images_cv2]
    for i in progress.tqdm(range(num_images, 0, -1), desc="Resizing images"):
        inner_image = images_resized[i]
        image = images_resized[i - 1]
        inner_image = resize_scale(inner_image, 1.0 / zoom)

        h, w = image.shape[:2]
        ih, iw = inner_image.shape[:2]
        x = int((w - iw) / 2)
        y = int((h - ih) / 2)

        image[y:y + ih, x:x + iw] = inner_image

        images_resized[i] = image

    images_cv2 = images_resized

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
            raise gr.Error(f"Unsupported direction: {direction}")

        current_image_idx = ceil(current_zoom_log)
        local_zoom = zoom ** (current_zoom_log - current_image_idx + 1)

        if current_zoom_log == 0.0:
            frame_image = images_cv2[0]
        else:
            frame_image = images_cv2[current_image_idx]
            frame_image = zoom_crop_cv2(frame_image, local_zoom)

        frame_image = cv2.resize(frame_image, (width, height), interpolation=cv2.INTER_LANCZOS4)
        frame_path = os.path.join(tmp_dir_hash, f"{i:06d}.png")
        cv2.imwrite(frame_path, frame_image)

    progress(0, desc=f"Creating {num_frames} frames")

    with ThreadPoolExecutor(8) as executor:
        list(progress.tqdm(executor.map(process_frame, range(num_frames)), total=num_frames, desc="Creating frames"))

    # Write video
    progress(0, desc=f"Writing video to: {output}")
    image_files = [
        os.path.join(tmp_dir_hash, f"{i:06d}.png") for i in range(num_frames)
    ]

    # Create video clip using images in tmp dir and audio if provided
    frame_size = (width, height)
    out = cv2.VideoWriter(output, cv2.VideoWriter_fourcc(*'mp4v'), fps, frame_size)
    for i in progress.tqdm(range(num_frames), desc="Writing video"):
        frame = cv2.imread(image_files[i])
        out.write(frame)
    out.release()

    if audio_path is not None:
        audio = AudioFileClip(audio_path.name)
        video = VideoFileClip(output)
        audio = audio.subclip(0, video.end)
        video = video.set_audio(audio)
        video_write_kwargs = {"audio_codec": "aac"}
        output_audio = os.path.splitext(output)[0] + "_audio.mp4"
        video.write_videofile(output_audio, **video_write_kwargs)
        output = output_audio

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
