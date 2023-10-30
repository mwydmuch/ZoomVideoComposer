# ZoomVideoComposer

This script aims to help to create zoom out/in videos from the set of images (generated, for example, with [Midjourney 5.2+ zoom out feature](https://docs.midjourney.com/docs/zoom-out) or other AI tools like Stable Diffusion or Photoshop) in a few minutes (depending on the number of images used of course).

Features:

- The script uses a correct interpolation for zooming that doesn't cause the effect of speeding up/and slowing down, which is noticeable in some zoom videos.
- It implements some basic image blending, so the transitions between images seem to be more smooth.
- It allows to set video duration, resolution, frame rate, direction of zoom, and easing.
- It can optionally add audio to the generated video.

Limitations:

- Currently, the zoom factor/ratio between all the images needs to be the same.
- At the moment, the images need to be perfectly centered (Midjourney 5.2 zoom out feature from time to time shifts the image that is zoomed out, and such images might not look good in the video).

I created it for myself to make experimentation with Midjourney easier for me. I might have missed some possible use cases, so if something is not working for you or you would like to have some feature, please let me know, and I will try to fix/improve it. Contributions are welcome, just open a PR.

## Usage

To use the script, you need to have Python installed on your machine.
You can download it [here](https://www.python.org/downloads/) if you are using Windows.
MacOS and Linux users should have Python installed by default.

1. [Download this repository](https://github.com/mwydmuch/ZoomVideoComposer/archive/refs/tags/0.3.2.zip), unpack it, and open the terminal/command line window in the root of the repository.

2. Install the required packages by running the following command in the terminal/cmd window:

```
pip install -r requirements.txt
```

3. Save images to one folder and rename them so that their lexicographic order matches the order you want them to appear in the video. For example, if you have 10 images, name them something like `00001.png`, `00002.png`, ..., `00010.png`.

4. Start the web UI by running the `gradio_ui.py` and open http://127.0.0.1:7860 in your web browser to use it.

or

4. Run the `zoom_video_composer.py` script providing a path to the folder with the images you want to use to create the video (you can also provide paths to each image separately in a specific order) and other options as specified below:

```
Usage: zoom_video_composer.py [OPTIONS] IMAGE_PATHS...

  Compose a zoom video from multiple provided images.

Options:
  -a, --audio-path FILE           Audio file path that will be added to the
                                  video.
  -z, --zoom FLOAT                Zoom factor/ratio between images.  [default:
                                  2.0]
  -d, --duration FLOAT            Duration of the video in seconds.  [default:
                                  10.0]
  -e, --easing [linear|linearWithInOutEase|easeInSine|easeOutSine|easeInOutSine|easeInQuad|easeOutQuad|easeInOutQuad|easeInCubic|easeOutCubic|easeInOutCubic|easeInPow|easeOutPow|easeInOutPow]
                                  Easing function.  [default: easeInOutSine]
  --easing-power FLOAT            Power argument of easeInPow, easeOutPow and
                                  easeInOutPow easing functions.  [default:
                                  1.5]
  --ease-duration FLOAT           Duration of easing in linearWithInOutEase as
                                  a fraction of video duration.  [default:
                                  0.02]
  -D, --direction [in|out|inout|outin]
                                  Zoom direction. Inout and outin combine both
                                  directions.  [default: out]
  -f, --fps INTEGER               Frames per second of the output video.
                                  [default: 30]
  -w, --width FLOAT               Width of the output video. Values > 1 are
                                  interpreted as specific sizes in pixels.
                                  Values <= 1 are interpreted as a fraction of
                                  the width of the first image.  [default: 1]
  -h, --height FLOAT              Height of the output video. Values > 1 are
                                  interpreted as specific sizes in pixels.
                                  Values <= 1 are interpreted as a fraction of
                                  the height of the first image.  [default: 1]
  -s, --resampling [nearest|box|bilinear|hamming|bicubic|lanczos]
                                  Resampling technique to use when resizing
                                  images.  [default: lanczos]
  -S, --super-sampling FLOAT      Scales the images by the provided factor.
                                  Values > 1 may increase the smoothness of
                                  the animation, when using very slow zooms.
                                  They increase the duration of the rendering.
                                  [default: 1.0]
  -m, --margin FLOAT              Size of the margin to cut from the edges of
                                  each image for better blending with the
                                  next/previous image. Values > 1 are
                                  interpreted as specific sizes in pixels.
                                  Values <= 1 are interpreted as a fraction of
                                  the smaller size of the first image.
                                  [default: 0.05]
  -o, --output PATH               Output video file.  [default: output.mp4]
  -t, --threads INTEGER           Number of threads to use to generate frames.
                                  Use values <= 0 for number of available
                                  threads on your machine minus the provided
                                  absolute value.  [default: -1]
  --tmp-dir PATH                  Temporary directory to store frames.
                                  [default: tmp]
  --keep-frames                   Keep frames in the temporary directory.
                                  Otherwise, it will be deleted after the
                                  video is generated.  [default: False]
  --skip-video-generation         Skip video generation. Useful if you only
                                  want to generate the frames. This option
                                  will keep the temporary directory similar to
                                  --keep-frames flag.  [default: False]
  --reverse-images                Reverse the order of the images.  [default:
                                  False]
  --image-engine [pil|cv2]        Image engine to use for image processing.
                                  [default: cv2]
  --resume                        Resume generation of the video.  [default:
                                  False]
  --blend-images-only             Stops after blending the input images.
                                  Inspecting the blended images is useful to
                                  detect any image-shifts or other artefacts
                                  before generating the video.  [default:
                                  False]
  --help                          Show this message and exit.
```

## Example of usage

Run in the root directory of the repository to generate an example video from the images in the `example` directory, a duration of 20 seconds that first zooms out and then zooms back in. The video will be saved in the `example_output.mp4` file.

```
python zoom_video_composer.py example -o example_output.mp4 -d 20 -D outin -e easeInOutSine
```

This example takes around 3 minutes to run on my Macbook Air M2. It can be speeded up by reducing the resolution of the output video and selecting faster resampling techniques like `bilinear`. The command below takes around 30 seconds to run on my Macbook Air M2, and can be used for a preview of the video before generating the final version (it reduces resolution to 512x512, framerate to 10 fps and uses a faster resampling technique).

```
python zoom_video_composer.py example -o example_output_faster.mp4 -d 20 -D outin -e easeInOutSine -f 10 -w 512 -h 512 -s bilinear
```

## Video tutorial and Google Colab for online use online

(Thanks to [u/OkRub6877](https://www.reddit.com/user/OkRub6877/))

You can watch the video tutorial on the tool [here](https://www.youtube.com/watch?v=nIJV_c-hKuw).
And use it online (without installing anything on your machine) using this [Google Colab](https://colab.research.google.com/drive/1lp_GF9Q8x5ckY7yQIA9zo37g-1TUGQ1T?usp=sharing).

## Tips for generating proper images with Midjourney

- Always use the same zoom factor for all images.
- Never use the vary option (`V1/2/3/4` and `Vary (Strong)/(Subtle)` buttons) on one of your images. It also changes the parts of the images generated previously, breaking the smoothness of the transition.
- Sometimes, Midjourney slightly changes the objects' position in the center when zooming out. It's recommended to avoid that by carefully selecting the images. It can also be fixed manually before running the script. See [Fix image shift](./guides/fix_image_shift.md)
- **`Zoom Out 1.5x` button in Midjourney is currently bugged and uses another zoom factor than `--zoom 1.5` prompt argument. To create an animation from images created with this button, use `-z 1.3333` argument for the script.**

## Tips on editing the images

The script stacks images on top of each other and blends them together.
The most zoomed-in images are always on top of less zoomed-in images,
so if you want to modify something on the images manually, you can do it only on the most zoomed-in image.

## Tips on how to generate images with Stable Diffusion or Photoshop

(Thanks to [u/ObiWanCanShowMe](https://www.reddit.com/user/ObiWanCanShowMe/))

### Stable Diffusion

To create a zoom out image in Stable Diffusion, you can:

1. Create an image.
2. Outpaint to a multiplier of canvas size (e.g., 2x)
3. Resize down to the original size.

Repeat until you get the desired number of images.

### Photoshop

You can also create proper images using Photoshop:

1. Create an image.
2. Resize an image to a multiplier of canvas size (e.g., 2x) and use generative fill on the empty space
3. Resize down to the original size.

Repeat until you get the desired number of images.

## Animations created with ZoomVideoComposer

- [Cats living in the abandoned city](https://www.reddit.com/r/midjourney/comments/14jcyqs/cats_living_in_the_abandoned_city_my_first_zoom/) (the example animation)
- [Red diamond](https://www.youtube.com/watch?v=XT2l0MkkwrQ) (1m40)
- [Primordial crowd](https://www.youtube.com/watch?v=A012FxOSqKY) (2m06)
- [Concept Trailer "A.I. Noir - Berlin City Crime Stories"](https://www.youtube.com/watch?v=7rAQjomKSPo) (2m00)
- [Midjourney Seamless Zoom Loop](https://www.youtube.com/shorts/WQx3tBoBhBY)
- [Trip down the mountain](https://www.youtube.com/watch?v=bB1R0MQRAYc) (1m05)

Add your animations here by creating a pull request.

## Projects using ZoomVideoComposer

- [GoAPI Midjourney ZoomVideo Generator](https://huggingface.co/spaces/GoAPI/Midjourney-zoom-video-generator-GoAPI) - creates zoom video from a set of prompts using [GoAPI Midjourney API](https://www.goapi.ai/midjourney-api) to generate images.

## TODOs

- [ ] Implement better (more smooth) blending of images.
- [ ] Add techniques to automatically center shifted images.
