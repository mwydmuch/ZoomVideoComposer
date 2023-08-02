import os
from math import cos, pi, sin, pow, ceil

import cv2
import gradio as gr
from PIL import Image
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from proglog import TqdmProgressBarLogger
from tqdm import trange


# Image classes - PIL and CV2
class ImageWrapper(object):
    def __init__(self):
        self.width = 0
        self.height = 0

    @staticmethod
    def load(image_path):
        raise NotImplementedError

    def save(self, image_path):
        raise NotImplementedError

    def resize(self, size, resampling_func):
        raise NotImplementedError

    def crop(self, crop_box):
        raise NotImplementedError

    def paste(self, image, x, y):
        raise NotImplementedError

    def zoom_crop(self, zoom, resampling_func):
        zoom_size = (int(self.width * zoom), int(self.height * zoom))
        crop_box = (
            int((zoom_size[0] - self.width) / 2),
            int((zoom_size[1] - self.height) / 2),
            int((zoom_size[0] + self.width) / 2),
            int((zoom_size[1] + self.height) / 2),
        )
        return self.resize(zoom_size, resampling_func).crop(crop_box)

    def resize_scale(self, scale, resampling_func):
        return self.resize(
            (int(self.width * scale), int(self.height * scale)), resampling_func
        )


class ImageCV2(ImageWrapper):
    def __init__(self, image):
        super().__init__()
        self.image = image
        self.height, self.width = self.image.shape[:2]

    @staticmethod
    def load(image_path):
        return ImageCV2(cv2.imread(image_path))

    def save(self, image_path):
        cv2.imwrite(image_path, self.image)

    def resize(self, size, resampling_func):
        new_image = cv2.resize(self.image, size, interpolation=resampling_func)
        return ImageCV2(new_image)

    def crop(self, crop_box):
        new_image = self.image[crop_box[1] : crop_box[3], crop_box[0] : crop_box[2]]
        return ImageCV2(new_image)

    def paste(self, image, x, y):
        self.image[y : y + image.height, x : x + image.width] = image.image


class ImagePIL(ImageWrapper):
    def __init__(self, image):
        self.image = image
        self.width = self.image.width
        self.height = self.image.height

    @staticmethod
    def load(image_path):
        return ImagePIL(Image.open(image_path))

    def save(self, image_path):
        self.image.save(image_path)

    def resize(self, size, resampling_func):
        new_image = self.image.resize(size, resampling_func)
        return ImagePIL(new_image)

    def crop(self, crop_box):
        new_image = self.image.crop(crop_box)
        return ImagePIL(new_image)

    def paste(self, image, x, y):
        self.image.paste(image.image, (x, y))


# Easing and resampling functions

# Gennerat family of power-based easing functions
def get_ease_pow_in(power, **kwargs):
    return lambda x: pow(x, power)


def get_ease_pow_out(power, **kwargs):
    return lambda x: 1 - pow(1 - x, power)


def get_ease_pow_in_out(power, **kwargs):
    return (
        lambda x: pow(2, power - 1) * pow(x, power)
        if x < 0.5
        else 1 - pow(-2 * x + 2, power) / 2
    )


# Returns an linear easing function with in and out ease
# This is useful for very long animations 
# where you want a steady zoom speed but still start and stop smoothly.
def get_linear_with_in_out_ease(ease_duration, **kwargs):
    # fraction defines both the x and y of the 'square' in which the easing takes place
    ease_duration_scale = 1 / ease_duration
    def linear_ease_in_out(x):
        if x < ease_duration:
            return (x * ease_duration_scale) ** 2 / ease_duration_scale / 2
        elif x > (1 - ease_duration):
            return 1 - ((1 - x) * ease_duration_scale) ** 2 / ease_duration_scale / 2
        else:
            return (x - ease_duration) * (1 - ease_duration) / (1 - 2 * ease_duration) + ease_duration / 2
    return linear_ease_in_out      


EASING_FUNCTIONS = {
    "linear": lambda x: x,
    "linearWithInOutEase": get_linear_with_in_out_ease,
    "easeInSine": lambda x: 1 - cos((x * pi) / 2),
    "easeOutSine": lambda x: sin((x * pi) / 2),
    "easeInOutSine": lambda x: -(cos(pi * x) - 1) / 2,
    "easeInQuad": get_ease_pow_in(power=2),
    "easeOutQuad": get_ease_pow_out(power=2),
    "easeInOutQuad": get_ease_pow_in_out(power=2),
    "easeInCubic": get_ease_pow_in(power=3),
    "easeOutCubic": get_ease_pow_out(power=3),
    "easeInOutCubic": get_ease_pow_in_out(power=3),
    "easeInPow": get_ease_pow_in,
    "easeOutPow": get_ease_pow_out,
    "easeInOutPow": get_ease_pow_in_out,
}
DEFAULT_EASING_KEY = "easeInOutSine"
DEFAULT_EASING_POWER = 1.5
DEFAULT_EASE_DURATION = 0.02

def get_easing_function(easing, power, ease_duration):
    easing_func = EASING_FUNCTIONS.get(easing, None)
    if easing_func is None:
        raise ValueError(f"Unsupported easing function: {easing}")
    if easing_func.__code__.co_varnames[0] != "x":
        easing_func = easing_func(power=power, ease_duration=ease_duration)
    return easing_func


# Image engines and resampling functions
IMAGE_CLASSES = {
    "pil": ImagePIL,
    "cv2": ImageCV2,
}
DEFAULT_IMAGE_ENGINE = "cv2"
RESAMPLING_FUNCTIONS_CV2 = {
    "nearest": cv2.INTER_NEAREST,
    "box": cv2.INTER_AREA,
    "bilinear": cv2.INTER_LINEAR,
    "hamming": cv2.INTER_LINEAR_EXACT,
    "bicubic": cv2.INTER_CUBIC,
    "lanczos": cv2.INTER_LANCZOS4,
}
RESAMPLING_FUNCTIONS_PIL = {
    "nearest": Image.Resampling.NEAREST,
    "box": Image.Resampling.BOX,
    "bilinear": Image.Resampling.BILINEAR,
    "hamming": Image.Resampling.HAMMING,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}
RESAMPLING_FUNCTIONS = {
    "pil": RESAMPLING_FUNCTIONS_PIL,
    "cv2": RESAMPLING_FUNCTIONS_CV2,
}
DEFAULT_RESAMPLING_KEY = "lanczos"


def get_resampling_function(resampling, image_engine):
    available_resampling_func = RESAMPLING_FUNCTIONS.get(image_engine, None)
    if available_resampling_func is None:
        raise ValueError(f"Unsupported image engine function: {resampling}")

    resampling_func = available_resampling_func.get(resampling, None)
    if resampling_func is None:
        raise ValueError(f"Unsupported resampling function: {resampling}")

    return resampling_func


# Helper functions of the zoom_video_composer.py
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


def read_images(image_paths, logger, image_engine=DEFAULT_IMAGE_ENGINE):
    image_class = IMAGE_CLASSES.get(image_engine, None)
    if image_class is None:
        raise ValueError(f"Unsupported image engine function: {image_class}")

    images = []
    for image_path in image_paths:
        if not image_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            logger(f"Unsupported file type: {image_path}, skipping")
            continue
        image = image_class.load(image_path)
        images.append(image)

    if len(images) < 2:
        raise ValueError("At least two images are required to create a zoom video")

    return images


def get_image_paths(input_paths):
    image_paths = []
    for path in input_paths:
        if hasattr(path, "name"):
            image_paths.append(path.name)
        elif os.path.isfile(path):
            image_paths.append(path)
        elif os.path.isdir(path):
            for subpath in sorted(os.listdir(path)):
                image_paths.append(os.path.join(path, subpath))
        else:
            raise ValueError(f"Unsupported file type: {path}, skipping")
    return image_paths


def get_sizes(image, width, height, margin):
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


def blend_images(images, margin, zoom, resampling_func):
    num_images = len(images) - 1
    for i in range(1, num_images + 1):
        inner_image = images[i]
        outer_image = images[i - 1]
        inner_image = inner_image.crop(
            (margin, margin, inner_image.width - margin, inner_image.height - margin)
        )

        image = outer_image.zoom_crop(zoom, resampling_func)
        image.paste(inner_image, margin, margin)
        images[i] = image

    image_resized = images[num_images].resize_scale(zoom, resampling_func)
    for i in range(num_images, 0, -1):
        inner_image = image_resized
        next_image_resized = images[i - 1].resize_scale(zoom, resampling_func)
        image = next_image_resized
        inner_image = inner_image.resize_scale(1.0 / zoom, resampling_func)

        image.paste(
            inner_image,
            int((image.width - inner_image.width) / 2),
            int((image.height - inner_image.height) / 2),
        )
        image_resized = next_image_resized
        images[i] = image

    return images


def process_frame(
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
):
    if direction == "in":
        current_zoom_log = zoom_in_log(easing_func, i, num_frames, num_images)
    elif direction == "out":
        current_zoom_log = zoom_out_log(easing_func, i, num_frames, num_images)
    elif direction == "inout":
        if i < num_frames_half:
            current_zoom_log = zoom_in_log(easing_func, i, num_frames_half, num_images)
        else:
            current_zoom_log = zoom_out_log(
                easing_func, i - num_frames_half, num_frames_half, num_images
            )
    elif direction == "outin":
        if i < num_frames_half:
            current_zoom_log = zoom_out_log(easing_func, i, num_frames_half, num_images)
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
        frame = frame.zoom_crop(local_zoom, resampling_func)

    frame = frame.resize((width, height), resampling_func)
    frame_path = os.path.join(tmp_dir_hash, f"{i:06d}.png")
    frame.save(frame_path)


def create_video_clip(output_path, fps, num_frames, tmp_dir_hash, audio_path, threads):
    image_files = [
        os.path.join(tmp_dir_hash, f"{i:06d}.png") for i in range(num_frames)
    ]
    video_clip = ImageSequenceClip(image_files, fps=fps)
    video_write_kwargs = {"codec": "libx264", "threads": threads}

    # Add audio
    if audio_path:
        audio_clip = AudioFileClip(audio_path)
        audio_clip = audio_clip.subclip(0, video_clip.end)
        video_clip = video_clip.set_audio(audio_clip)
        video_write_kwargs["audio_codec"] = "aac"

    video_clip.write_videofile(
        output_path,
        logger=TqdmProgressBarLogger(
            bars={
                "t": {
                    "title": "Writting the movie file",
                    "total": num_frames,
                    "message": None,
                    "index": -1,
                }
            },
            print_messages=False,
        ),
        **video_write_kwargs,
    )
