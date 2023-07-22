# Fix image shift

It sometimes happens that Midjourney shifts the image slightly on the zoom out. This should be fixed before creating the animation to achieve a smooth transition.

## Fix image shift in Photoshop

The image where the shift happened during zooming out is called *image 2* in this guide, and the one before it *image 1*.
The guide presents steps for Photoshop. However, they can be easily replicated in other image editors.


### Fix image 2

* Open image 2

  ![step1](fix_image_shift_step_1.png)
  
* Place image 1 on top and **transform** it `50%, 50%`, if you used zoom out factor = 2, otherwise use `(100 / zoom)%, (100 / zoom)%` value.

  ![step2](fix_image_shift_step_2.png)
  
* Select image 2, **Edit > Transform > Warp**, choose **Grid: 4 x 4** and select the center control points.

  ![step3](fix_image_shift_step_3.png)
  
* Move the control points until it matches image 1.
 
  ![step4](fix_image_shift_step_4.png)
  
* Add a mask to image 1 and with a soft brush, paint over the edges to blend both images. Make sure to only work on the edges and work with the minimal width possible.

  ![step5 mask](fix_image_shift_step_5_mask.png)

* Image 2 is now ready. 

  ![step5](fix_image_shift_step_5.png)
  
### Fix image 1

Depending on how substantial the edits on image 2 are, it might be necessary to fix image 1 too, to cover up the tweaks on the edges.

* Open image 1

  ![step6](fix_image_shift_step_6.png)
  
* Place the **fixed** version of image 2 on top.

* Add a mask to image 2 and invert it to completely hide it.

* With a white brush, reveal the edges.

* Image 1 is now ready.

  ![step7](fix_image_shift_step_7.png)
  
## Result

Before and after:

https://github.com/sambernaerdt/ZoomVideoComposer/assets/4118556/b8dcec1f-b386-4df1-ab47-4ac9da89505f

https://github.com/sambernaerdt/ZoomVideoComposer/assets/4118556/91ffd252-dcd3-4bb5-aeef-616cf8685e7f

