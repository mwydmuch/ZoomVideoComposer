# from zoom_video_composer import function and use it in gradio

import gradio as gr
from zoom_video_composer import zoom_video_composer, VERSION, EASING_FUNCTIONS, DEFAULT_EASING_KEY, RESAMPLING_FUNCTIONS_PIL, DEFAULT_RESAMPLING_KEY

grInputs = [
    gr.File(file_count="multiple", label="Upload images as folder", file_types=["image"]),
    gr.File(file_count="single", label="Upload audio", file_types=["audio"], scale=1),
    gr.inputs.Slider(label="Zoom factor/ratio between images", minimum=1.0, maximum=5.0, step=0.01, default=2.0),
    gr.inputs.Slider(label="Duration of the video in seconds", minimum=1.0, maximum=300.0, step=0.1, default=10.0),
    gr.inputs.Dropdown(label="Easing function used for zooming",
                       choices=list(EASING_FUNCTIONS.keys()),
                       default=DEFAULT_EASING_KEY),
    gr.inputs.Dropdown(label="Zoom direction. Inout and outin combine both directions",
                       choices=["in", "out", "inout", "outin"], default="out"),
    gr.inputs.Slider(label="Frames per second of the output video", minimum=1, maximum=120, step=1, default=30),
    gr.inputs.Checkbox(label="Reverse images", default=False),
    gr.inputs.Slider(label="Output width multiplier", minimum=0.1, maximum=2, step=0.01, default=1),
    gr.inputs.Slider(label="Output height multiplier", minimum=0.1, maximum=2, step=0.01, default=1),
    gr.inputs.Dropdown(label="Resampling function used for resizing", choices=list(RESAMPLING_FUNCTIONS_PIL.keys()),
                          default=DEFAULT_RESAMPLING_KEY),
    gr.inputs.Slider(label="Blending margin", minimum=0.0, maximum=0.25, step=0.01, default=0.05),
    gr.inputs.Textbox(label="Output video file", default="output.mp4")
]

def zoom_video_composer_gradio(
        image_paths,
        audio_path,
        zoom,
        duration,
        easing,
        direction,
        fps,
        reverse_images,
        width,
        height,
        resampling,
        margin,
        output,
        progress=gr.Progress(track_tqdm=True)):
    return zoom_video_composer(
        image_paths,
        audio_path=audio_path,
        zoom=zoom,
        duration=duration,
        easing=easing,
        direction=direction,
        fps=fps,
        reverse_images=reverse_images,
        width=width,
        height=height,
        resampling=resampling,
        margin=margin,
        output=output,
    )

iface = gr.Interface(
    fn=zoom_video_composer_gradio,
    inputs=grInputs,
    outputs=[gr.outputs.Video(label="Video")],
    title=f"Zoom Video Composer {VERSION}",
    description="Generate a zoom video from multiple provided images.",
    allow_flagging=False,
    allow_screenshot=True,
    allow_embedding=True,
    allow_download=True)

iface.queue(concurrency_count=1).launch()
