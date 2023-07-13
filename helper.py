import os
from math import cos, pi, sin, pow, ceil

import click
import cv2
import gradio as gr
from PIL import Image
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from tqdm import trange

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
IMAGE_ENGINES = ["pil", "cv2"]
DEFAULT_IMAGE_ENGINE = "cv2"
IMAGE_ENGINE = DEFAULT_IMAGE_ENGINE
DEFAULT_EASING_KEY = "easeInOutSine"
DEFAULT_EASING_FUNCTION = EASING_FUNCTIONS[DEFAULT_EASING_KEY]
RESAMPLING_FUNCTIONS = {
    "nearest": cv2.INTER_NEAREST if IMAGE_ENGINE == "cv2" else Image.NEAREST,
    "box": cv2.INTER_AREA if IMAGE_ENGINE == "cv2" else Image.BOX,
    "bilinear": cv2.INTER_LINEAR if IMAGE_ENGINE == "cv2" else Image.BILINEAR,
    "hamming": cv2.INTER_LINEAR_EXACT if IMAGE_ENGINE == "cv2" else Image.HAMMING,
    "bicubic": cv2.INTER_CUBIC if IMAGE_ENGINE == "cv2" else Image.BICUBIC,
    "lanczos": cv2.INTER_LANCZOS4 if IMAGE_ENGINE == "cv2" else Image.LANCZOS,
}
DEFAULT_RESAMPLING_KEY = "lanczos"
DEFAULT_RESAMPLING_FUNCTION = RESAMPLING_FUNCTIONS[DEFAULT_RESAMPLING_KEY]


def zoom_crop_cv2(image, zoom, resampling_func=RESAMPLING_FUNCTIONS["lanczos"]):
    height, width, channels = image.shape
    zoom_size = (int(width * zoom), int(height * zoom))
    # crop box as integers
    crop_box = (
        int((zoom_size[0] - width) / 2),
        int((zoom_size[1] - height) / 2),
        int((zoom_size[0] + width) / 2),
        int((zoom_size[1] + height) / 2),
    )
    im = cv2.resize(image, zoom_size, interpolation=resampling_func)
    im = im[crop_box[1]:crop_box[3], crop_box[0]:crop_box[2]]
    return im


def zoom_crop_pil(image, zoom, resampling_func=RESAMPLING_FUNCTIONS["lanczos"]):
    width, height = image.size
    zoom_size = (int(width * zoom), int(height * zoom))
    crop_box = (
        (zoom_size[0] - width) / 2,
        (zoom_size[1] - height) / 2,
        (zoom_size[0] + width) / 2,
        (zoom_size[1] + height) / 2,
    )
    return image.resize(zoom_size, resampling_func).crop(crop_box)


def zoom_crop(image, zoom, resampling_func=RESAMPLING_FUNCTIONS["lanczos"]):
    if IMAGE_ENGINE == "cv2":
        return zoom_crop_cv2(image, zoom, resampling_func)
    else:
        return zoom_crop_pil(image, zoom, resampling_func)


def resize_scale_cv2(image, scale, resampling_func=RESAMPLING_FUNCTIONS["lanczos"]):
    height, width = image.shape[:2]
    return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=resampling_func)


def resize_scale_pil(image, scale, resampling_func=RESAMPLING_FUNCTIONS["lanczos"]):
    width, height = image.size
    return image.resize((int(width * scale), int(height * scale)), resampling_func)


def resize_scale(image, scale, resampling_func=RESAMPLING_FUNCTIONS["lanczos"]):
    if IMAGE_ENGINE == "cv2":
        return resize_scale_cv2(image, scale, resampling_func)
    else:
        return resize_scale_pil(image, scale, resampling_func)


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


def read_images(image_paths):
    images = []
    for image_path in image_paths:
        if not image_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            click.echo(f"Unsupported file type: {image_path}, skipping")
            continue
        if IMAGE_ENGINE == "cv2":
            image = cv2.imread(image_path)
        else:
            image = Image.open(image_path)
        images.append(image)

    if len(images) < 2:
        raise ValueError("At least two images are required to create a zoom video")

    return images


def get_image_paths(image_paths):
    _image_paths = []
    for image_path in image_paths:
        # if image_path is _TemporaryFileWrapper
        if hasattr(image_path, "name"):
            _image_paths.append(image_path.name)
        elif os.path.isfile(image_path):
            _image_paths.append(image_path)
        elif os.path.isdir(image_path):
            for subimage_path in sorted(os.listdir(image_path)):
                _image_paths.append(os.path.join(image_path, subimage_path))
        else:
            raise ValueError(f"Unsupported file type: {image_path}, skipping")
    return _image_paths


def get_sizes(image, width, height, margin):
    if IMAGE_ENGINE == "cv2":
        h, w, _ = image.shape
        width = get_px_or_fraction(width, w)
        height = get_px_or_fraction(height, h)
        margin = get_px_or_fraction(margin, min(w, h))
    else:
        width = get_px_or_fraction(width, image.width)
        height = get_px_or_fraction(height, image.height)
        margin = get_px_or_fraction(margin, min(image.width, image.height))

    return width, height, margin


def images_reverse(images, direction, reverse_images):
    if direction in ["out", "outin"]:
        images.reverse()
    if reverse_images:
        images.reverse()
    return images


def blend_images_cv2(images, margin, zoom, resampling_func):
    num_images = len(images) - 1
    for i in trange(1, num_images + 1):
        inner_image = images[i]
        outer_image = images[i - 1]
        inner_image = inner_image[
                      margin:inner_image.shape[0] - margin,
                      margin:inner_image.shape[1] - margin
                      ]
        image = zoom_crop(outer_image, zoom)
        image[
        margin:margin + inner_image.shape[0],
        margin:margin + inner_image.shape[1]
        ] = inner_image
        images[i] = image

    images_resized = [resize_scale(i, zoom) for i in images]
    for i in trange(num_images, 0, -1):
        inner_image = images_resized[i]
        image = images_resized[i - 1]
        inner_image = resize_scale(inner_image, 1.0 / zoom, resampling_func)

        h, w = image.shape[:2]
        ih, iw = inner_image.shape[:2]
        x = int((w - iw) / 2)
        y = int((h - ih) / 2)

        image[y:y + ih, x:x + iw] = inner_image

        images_resized[i] = image

    images = images_resized
    return images


def blend_images_pil(images, margin, zoom, resampling_func):
    num_images = len(images) - 1
    for i in trange(1, num_images + 1):
        inner_image = images[i]
        outer_image = images[i - 1]
        inner_image = inner_image.crop(
            (margin, margin, inner_image.width - margin, inner_image.height - margin)
        )

        image = zoom_crop(outer_image, zoom, resampling_func)
        image.paste(inner_image, (margin, margin))
        images[i] = image

    images_resized = [resize_scale(i, zoom, resampling_func) for i in images]
    for i in trange(num_images, 0, -1):
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
    return images


def blend_images(images, margin, zoom, resampling_func):
    if IMAGE_ENGINE == "cv2":
        images_resized = blend_images_cv2(images, margin, zoom, resampling_func)
    else:
        images_resized = blend_images_pil(images, margin, zoom, resampling_func)
    return images_resized


def process_frame_pil(i, images, direction, easing_func, num_frames, num_frames_half, num_images, zoom, width, height,
                      resampling_func, tmp_dir_hash):
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


def process_frame_cv2(i, images, direction, easing_func, num_frames, num_frames_half, num_images, zoom, width,
                      height, resampling_func, tmp_dir_hash):
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
        frame_image = images[0]
    else:
        frame_image = images[current_image_idx]
        frame_image = zoom_crop(frame_image, local_zoom)

    frame_image = cv2.resize(frame_image, (width, height), interpolation=resampling_func)
    frame_path = os.path.join(tmp_dir_hash, f"{i:06d}.png")
    cv2.imwrite(frame_path, frame_image)


def process_frame(i, images, direction, easing_func, num_frames, num_frames_half, num_images, zoom, width, height,
                  resampling_func, tmp_dir_hash):
    if IMAGE_ENGINE == "cv2":
        process_frame_cv2(i, images, direction, easing_func, num_frames, num_frames_half, num_images, zoom, width,
                          height, resampling_func, tmp_dir_hash)
    else:
        process_frame_pil(i, images, direction, easing_func, num_frames, num_frames_half, num_images, zoom, width,
                          height, resampling_func, tmp_dir_hash)


def create_video_clip(audio_path, fps, height, image_engine, image_files, num_frames, output, tmp_dir_hash, width):
    if image_engine == "cv2":
        frame_size = (width, height)
        out = cv2.VideoWriter(output, cv2.VideoWriter.fourcc(*'mp4v'), fps, frame_size)
        for image_file in image_files:
            img = cv2.imread(image_file)
            out.write(img)
        out.release()
    else:
        click.echo(f"Writing video to: {output} ...")
        image_files = [os.path.join(tmp_dir_hash, f"{i:06d}.png") for i in range(num_frames)]
        video_clip = ImageSequenceClip(image_files, fps=fps)
        video_write_kwargs = {"codec": "libx264"}
        video_clip.write_videofile(output, **video_write_kwargs)
    if audio_path is not None:
        audio = AudioFileClip(audio_path.name)
        video = VideoFileClip(output)
        audio = audio.subclip(0, video.end)
        video = video.set_audio(audio)
        video_write_kwargs = {"audio_codec": "aac"}
        output_audio = os.path.splitext(output)[0] + "_audio.mp4"
        video.write_videofile(output_audio, **video_write_kwargs)
        output = output_audio
    return output
