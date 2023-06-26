# ZoomVideoComposer

This script aims to help to create zoom out/in videos from the set of images (generated, for example, with [Midjourney 5.2 zoom out feature](https://docs.midjourney.com/docs/zoom-out) or other AI tools like Stable Diffusion or Photoshop) in a few minutes (depending on the number of images used of course).

Features:
- The script uses a correct interpolation for zooming that doesn't cause the effect of speeding up/and slowing down, which is noticeable in some zoom videos.
- It implements some basic image blending, so the transitions between images seem to be more smooth.
- It allows to set video duration, resolution, frame rate, direction of zoom, and easing.
- It can optionally add audio to the generated video.

Limitations:
- Currently, the zoom factor/ratio between all the images needs to be the same.
- At the moment, the images need to be perfectly centered (Midjourney 5.2 zoom out feature from time to time shifts the image that is zoomed out, and such images might not look good in the video).


I create it for myself to make experimentation with Midjourney easier for me. I've might miss some possible use cases, so if something is not working for you, or you would like to have some feature, please let me know I will try to fix/improve it. Contributions are welcome.


## Usage

To use the script, you need to have Python installed on your machine. 
You can download it [here](https://www.python.org/downloads/) if you are using Windows. 
MacOS and Linux users should have Python installed by default.

1. Download this repository and open the terminal/command line window in the root of the repository.

2. Install the required packages by running the following command in the terminal/cmd window:
```
pip install -r requirements.txt
```

3. Save images to one folder and rename them so that their lexicographic order matches the order you want them to appear in the video. For example, if you have 10 images, name them something like `00001.png`, `00002.png`, ..., `00010.png`.

4. Run a script providing a path to the folder with the images you want to use to create the video (you can also provide paths to each image separately in a specific order) and other options as specified below: 
```
Usage: zoom_video_composer.py [OPTIONS] IMAGE_PATHS...

  Compose a zoom video from multiple provided images.

Options:
  -a, --audio_path FILE           Audio file path that will be added to the
                                  video.
  -z, --zoom FLOAT                Zoom factor/ratio between images.  [default:
                                  2.0]
  -d, --duration FLOAT            Duration of the video in seconds.  [default:
                                  10.0]
  -e, --easing [linear|easeInSine|easeOutSine|easeInOutSine|easeInQuad|easeOutQuad|easeInOutQuad|easeInCubic|easeOutCubic|easeInOutCubic]
                                  Easing function.  [default: easeInOutSine]
  -r, --direction [in|out|inout|outin]
                                  Zoom direction. Inout and outin combine both
                                  directions.  [default: out]
  -o, --output PATH               Output video file.  [default: output.mp4]
  -t, --threads INTEGER           Number of threads to use to generate frames.
                                  Use values <= 0 for number of available
                                  threads on your machine minus the provided
                                  absolute value.  [default: -1]
  --tmp-dir PATH                  Temporary directory to store frames.
                                  [default: tmp]
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
                                  Resampling techique to use when resizing
                                  images.  [default: lanczos]
  -m, --margin FLOAT              Size of the margin to cut from the edges of
                                  each image for better blending with the
                                  next/previous image. Values > 1 are
                                  interpreted as specific sizes in pixels.
                                  Values <= 1 are interpreted as a fraction of
                                  the smaller size of the first image.
                                  [default: 0.05]
  --keep-frames                   Keep frames in the temporary directory.
                                  Otherwise, it will be deleted after the
                                  video is generated.
  --skip-video-generation         Skip video generation. Useful if you only
                                  want to generate the frames. This option
                                  will keep the temporary directory similar to
                                  --keep-frames flag.
  --reverse-images                Reverse the order of the images.
  --help                          Show this message and exit.
```


## Example of usage

Run in the root directory of the repository to generate an example video from the images in the `example` directory, a duration of 20 seconds that first zooms out and then back in. The video will be saved in the `example_output.mp4` file.

```
python zoom_video_composer.py example -o example_output.mp4 -d 20 -r outin -e easeInOutSine
```

This example takes around 3 minutes to run on my Macbook Air M2. It can be speeded up by reducing the resolution of the output video and selecting faster resampling techniques like `bilinear`. The command below takes around 30 seconds to run on my Macbook Air M2, and can be used for a preview of the video before generating the final version (it reduces resolution to 512x512, framerate to 10 fps and uses faster resampling technique).

```
python zoom_video_composer.py example -o example_output_faster.mp4 -d 20 -r outin -e easeInOutSine -f 10 -w 512 -h 512 -s bilinear
```


## Tips for generating proper images with Midjourney

- Always use the same zoom factor for all images.
- Never use the vary option on one of your images. It also changes the parts of the images generated previously, breaking the smoothness of the transition.
- Sometimes, Midjourney slightly changes the objects' position in the center when zooming out. Nothing can be done with it now; be aware of that and select generations without such shifts.


## Tips on how to generate images with Stable Diffusion or Photoshop
Thanks to [u/ObiWanCanShowMe](https://www.reddit.com/user/ObiWanCanShowMe/)!

### Stable Diffusion

To create a zoom out image in Stable Diffusion you can:
1. Create an image.
2. Outpaint to a multiplier of canvas size (e.g. 2x)
3. Resize down to the original size.

Repeat until you get the desired number of images.

### Photoshop

You can also create proper images using photoshop:
1. Create an image.
2. Resize an image to a multiplier of canvas size (e.g. 2x) and use generative fill on the empty space
3. Resize down to the original size.

Repeat until you get the desired number of images.


## Animations created with this script

- [Cats living in the abandoned city](https://www.reddit.com/r/midjourney/comments/14jcyqs/cats_living_in_the_abandoned_city_my_first_zoom/)

Add your animations here by creating a pull request.


## TODOs

- [ ] Implement better blending of images.
- [ ] Add techniques to automatically center shifted images.
- [ ] Add GUI?
