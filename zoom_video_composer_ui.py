# from zoom_video_composer import function and use it in gradio

import gradio as gr
from zoom_video_composer import zoom_video_composer


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