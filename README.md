# ZoomVideoComposer

This script aims to help to create zoom out/in videos from the set of images (generated, for example, with [Midjourney 5.2 zoom out feature](https://docs.midjourney.com/docs/zoom-out)) in a few minutes (depending on the number of images used of course).

Features:
- The script uses a correct interpolation for zooming that doesn't cause the effect of speeding up/and slowing down, which is noticeable in some zoom videos.
- It implements some basic image blending, so the transitions between images seem to be more smooth.
- At the moment, it allows to set video duration, resolution, frame rate, direction of zoom, and easing.
- Very much work in progress. If something is not working for you, please let me know. Contributions are welcome.

Limitations:
- Currently, the zoom factor/ratio between all the images needs to be the same.
- At the moment, the images need to be perfectly centered (Midjourney 5.2 zoom out feature from time to time shifts the image that is zoomed out, and such images might not look good in the video).



## Usage

To use the script, you need to have Python installed on your machine. 
You can download it [here](https://www.python.org/downloads/) if you are using Windows. 
MacOS and Linux users should have Python installed by default.

1. Download this repository and open the terminal window in the root of the repository.

2. Install the required packages by running the following command in the terminal window:
```bash
pip install -r requirements.txt
```

3. Save images to one folder and rename them so that their lexicographic order matches the order you would like them to appear in the video. For example, if you have 10 images, name them `00001.png`, `00002.png`, ..., `00010.png`.

4. Run a script providing a path to the folder with the images you want to use to create the video (you can also provide paths to each image separately in order you would like them to appear in a video) and other options as specified below: 
```bash
Usage: zoom_video_composer.py [OPTIONS] IMAGE_PATHS...

  Compose a zoom video from multiple provided images.

Options:
  -z, --zoom FLOAT                Zoom factor/ratio between images. [default:
                                  2.0]
  -d, --duration FLOAT            Duration of the video in seconds. [default:
                                  10.0]
  -e, --easing [linear|easeInSine|easeOutSine|easeInOutSine|easeInQuad|easeOutQuad|easeInOutQuad|easeInCubic|easeOutCubic|easeInOutCubic]
                                  Easing function. [default: easeInOutSine]
  -r, --direction [in|out|inout|outin]
                                  Zoom direction. Inout and outin combine both
                                  directions. [default: out]
  -o, --output PATH               Output video file. [default: output.mp4]
  -t INTEGER                      Number of threads to use to generate frames.
                                  Use values <= 0 for number of available
                                  threads on your machine minus the provided
                                  absolute value. [default: -1]
  --tmp-dir PATH                  Temporary directory to store frames.
                                  [default: tmp]
  -f, --fps INTEGER               Frames per second of the output video.
                                  [default: 30]
  -w, --width INTEGER             Width of the output video. [default: 1024]
  -h, --height INTEGER            Height of the output video. [default: 1024]
  -s, --resampling [nearest|box|bilinear|hamming|bicubic|lanczos]
                                  Resampling techique to use when resizing
                                  images. [default: lanczos]
  -m, --margin INTEGER            Margin in pixels to cut from the edges of
                                  the images for better blending. [default:
                                  50]
  --keep-tmp                      Keep temporary directory. Otherwise, it will
                                  be deleted after the video is generated.
                                  [default: False]
  --reverse-images                Reverse the order of the images. [default:
                                  False]
  --help                          Show this message and exit.
```

## Example of usage

Run in the root directory of the repository to generate an example video from the images in the `example` directory, a duration of 20 seconds that first zooms out and then back in. The video will be saved in the `example_output.mp4` file.

```bash
python zoom_video_composer.py example -o example_output.mp4 -d 20 -r outin -e easeInOutSine
```

This example takes around 3 minutes to run on my Macbook Air M2. It can be speeded up by reducing the resolution of the output video and selecting faster resampling techniques like `bilinear`. The command below takes around 1.5 minutes to run on my Macbook Air M2:

```bash
python zoom_video_composer.py example -o example_output_faster.mp4 -d 20 -w 512 -h 512 -s bilinear -r outin -e easeInOutSine
```



## Tops for generating proper images with Midjourney

- Always use the same zoom factor for all images.
- Never use the vary option on one of your images, it also changes the parts of the images generated previously, breaking the smoothness of the transition.
- Sometimes, Midjourney slightly changes the objects' position in the center when zooming out. Nothing can be done with it now; be aware of that and select generations without such shifts.


## Animations created with this script

Add your animations here by creating a pull request.



## TODOs

- [ ] Implement better blending of images.
- [ ] Add techniques to automatically center shifted images.
- [ ] Add GUI?