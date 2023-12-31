# -*- coding: utf-8 -*-
# Copyright 2018 The Blueoil Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import time
import os
from time import sleep
from multiprocessing import Queue

import click
import cv2
import numpy as np

from lmnet.nnlib import NNLib
from multiprocessing import Pool
from lmnet.utils.config import (
    load_yaml,
    build_pre_process,
    build_post_process,
)
from lmnet.utils.demo import (
    add_rectangle,
    add_fps,
)

nn = None
pre_process = None
post_process = None


class MyTime:
    def __init__(self, function_name):
        self.start_time = time.time()
        self.function_name = function_name

    def show(self):
        print("TIME: ", self.function_name, time.time() - self.start_time)


def init_camera(camera_width, camera_height):
    if hasattr(cv2, 'cv'):
        vc = cv2.VideoCapture(0)
        vc.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, camera_width)
        vc.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, camera_height)
        vc.set(cv2.cv.CV_CAP_PROP_FPS, 10)

    else:
        vc = cv2.VideoCapture(1)
        vc.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        vc.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        vc.set(cv2.CAP_PROP_FPS, 10)

    return vc


def add_class_label(canvas,
                    text="Hello",
                    font=cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale=0.42,
                    font_color=(140, 40, 200),
                    line_type=1,
                    dl_corner=(50, 50)):
    cv2.putText(canvas, text, dl_corner, font, font_scale, font_color, line_type)


def run_inference(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    global nn, pre_process, post_process
    start = time.time()

    data = pre_process(image=img)["image"]
    data = np.asarray(data, dtype=np.float32)
    data = np.expand_dims(data, axis=0)

    start_time = time.time()
    result = nn.run(data)

    inference_time = time.time() - start_time
    result = post_process(outputs=result)['outputs']
    print('inference time: {:.3f}s'.format(inference_time))

    fps = 1.0/(time.time() - start)
    return result, fps


def clear_queue(queue):
    while not queue.empty():
        queue.get()
    return queue


def swap_queue(q1, q2):
    return q2, q1  # These results are swapped


def run_object_detection(config):
    global nn
    # Set variables
    camera_width = 320
    camera_height = 240
    window_name = "Object Detection Demo"
    input_width = config.IMAGE_SIZE[1]
    input_height = config.IMAGE_SIZE[0]

    vc = init_camera(camera_width, camera_height)

    pool = Pool(processes=1, initializer=nn.init)
    result = False
    fps = 1.0

    q_save = Queue()
    q_show = Queue()

    grabbed, camera_img = vc.read()

    q_show.put(camera_img.copy())
    input_img = camera_img.copy()

    #  ----------- Beginning of Main Loop ---------------
    while True:
        m1 = MyTime("1 loop of while(1) of main()")
        pool_result = pool.apply_async(run_inference, (input_img, ))
        is_first = True
        while True:
            grabbed, camera_img = vc.read()
            if is_first:
                input_img = camera_img.copy()
                is_first = False
            q_save.put(camera_img.copy())
            if not q_show.empty():
                window_img = q_show.get()
                if result:
                    window_img = add_rectangle(
                        config.CLASSES,
                        window_img,
                        result,
                        (input_height, input_width)
                    )
                    window_img = add_fps(window_img, fps)
                # ---------- END of if result != False -----------------

                cv2.imshow(window_name, window_img)
                key = cv2.waitKey(2)    # Wait for 2ms
                if key == 27:           # ESC to quit
                    return
            if pool_result.ready():
                break

        # -------------- END of wait loop ----------------------
        q_show = clear_queue(q_show)
        q_save, q_show = swap_queue(q_save, q_show)
        result, fps = pool_result.get()
        m1.show()

    # --------------------- End of main Loop -----------------------


def run_classification(config):
    global nn
    camera_height = 240
    camera_width = 320

    window_name = "Classification Demo"
    window_width = 320
    window_height = 240

    vc = init_camera(camera_width, camera_height)

    pool = Pool(processes=1, initializer=nn.init)

    grabbed, camera_img = vc.read()

    pool_result = pool.apply_async(run_inference, (camera_img, ))
    result = None
    fps = 1.0
    loop_count = 0

    while 1:

        m1 = MyTime("1 loop of while(1) of main()")
        key = cv2.waitKey(2)    # Wait for 2ms
        if key == 27:           # ESC to quit
            break

        m2 = MyTime("vc.read()")
        grabbed, camera_img = vc.read()
        m2.show()

        if pool_result.ready():
            result, fps = pool_result.get()
            pool_result = pool.apply_async(run_inference, (camera_img, ))

        if (window_width == camera_width) and (window_height == camera_height):
            window_img = camera_img
        else:
            window_img = cv2.resize(camera_img, (window_width, window_height))

        if result is not None:
            result_class = np.argmax(result, axis=1)
            add_class_label(window_img, text=str(result[0, result_class][0]), font_scale=0.52, dl_corner=(230, 230))
            add_class_label(window_img, text=config.CLASSES[result_class[0]], font_scale=0.52, dl_corner=(230, 210))
            window_img = add_fps(window_img, fps)
            loop_count += 1
            print("loop_count:", loop_count)

        m3 = MyTime("cv2.imshow()")
        cv2.imshow(window_name, window_img)
        m3.show()

        m1.show()
        sleep(0.05)

    cv2.destroyAllWindows()


def run(model, config_file):
    global nn, pre_process, post_process
    filename, file_extension = os.path.splitext(model)

    if not file_extension == '.so' or not file_extension == '.pb':
        raise Exception("""
            Unknown file type. Got %s%s.
            Please check the model file (-m). We only support .pb and .so files.
            """ % (filename, file_extension))

    config = load_yaml(config_file)
    pre_process = build_pre_process(config.PRE_PROCESSOR)
    post_process = build_post_process(config.POST_PROCESSOR)

    if file_extension == '.so':  # Shared library
        nn = NNLib()
        nn.load(model)

    elif file_extension == '.pb':  # Protocol Buffer file
        # only load tensorflow if user wants to use GPU
        from lmnet.tf_graph_load_pb import TFGraphLoadPb
        nn = TFGraphLoadPb(model)

    else:
        raise Exception("Unknown file type. Got %s." % (filename))

    if config.TASK == "IMAGE.CLASSIFICATION":
        run_classification(config)

    if config.TASK == "IMAGE.OBJECT_DETECTION":
        run_object_detection(config)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option(
    "-m",
    "--model",
    type=click.Path(exists=True),
    help=u"Inference Model filename",
    default="../models/lib/lib_fpga.so",
)
@click.option(
    "-c",
    "--config_file",
    type=click.Path(exists=True),
    help=u"Config file Path",
    default="../models/meta.yaml",
)
def main(model, config_file):
    run(model, config_file)


if __name__ == "__main__":
    main()
