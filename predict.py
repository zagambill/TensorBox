"""
This file is designed for prediction of bounding boxes for a single image.
Predictions could be made in two ways: command line style or service style. Command line style denotes that one can 
run this script from the command line and configure all options right in the command line. Service style allows 
to call :func:`initialize` function once and call :func:`hot_predict` function as many times as it needed to. 
"""

import tensorflow as tf
import os, json, subprocess
from optparse import OptionParser

from scipy.misc import imread, imresize
import numpy as np
from PIL import Image, ImageDraw

from train import build_forward
from utils.annolist import AnnotationLib as al
from utils.train_utils import add_rectangles, rescale_boxes
import json
# from utils.data_utils import Rotate90

strong_hypes_path = 'hypes/overfeat_rezoom.json'
strong_weights_path = ''

def initialize(weights_path, hypes_path, options=None):
    """Initialize prediction process.
    All long running operations like TensorFlow session start and weights loading are made here.
    Args:
        weights_path (string): The path to the model weights file. 
        hypes_path (string): The path to the hyperparameters file. 
        options (dict): The options dictionary with parameters for the initialization process.
    Returns (dict):
        The dict object which contains `sess` - TensorFlow session, `pred_boxes` - predicted boxes Tensor, 
          `pred_confidences` - predicted confidences Tensor, `x_in` - input image Tensor, 
          `hypes` - hyperparametets dictionary.
    """

    # H = prepare_options(strong_hypes_path, options)
    with open(strong_hypes_path, 'r') as f:
        H = json.load(f)

    print(H)

    tf.reset_default_graph()
    print(tf.float32)
    print(H['image_height'])

    x_in = tf.placeholder(tf.float32, name='x_in', shape=[H['image_height'], H['image_width'], 3])
    if H['use_rezoom']:
        pred_boxes, pred_logits, pred_confidences, pred_confs_deltas, pred_boxes_deltas \
            = build_forward(H, tf.expand_dims(x_in, 0), 'test', reuse=None)
        grid_area = H['grid_height'] * H['grid_width']
        pred_confidences = tf.reshape(
            tf.nn.softmax(tf.reshape(pred_confs_deltas, [grid_area * H['rnn_len'], H['num_classes']])),
            [grid_area, H['rnn_len'], H['num_classes']])
        if H['reregress']:
            pred_boxes = pred_boxes + pred_boxes_deltas
    else:
        pred_boxes, pred_logits, pred_confidences = build_forward(H, tf.expand_dims(x_in, 0), 'test', reuse=None)

    saver = tf.train.Saver()
    sess = tf.Session()
    # sess.run(tf.initialize_all_variables())
    sess.run(tf.global_variables_initializer())
    saver.restore(sess, weights_path)
    return {'sess': sess, 'pred_boxes': pred_boxes, 'pred_confidences': pred_confidences, 'x_in': x_in, 'hypes': H}


def hot_predict(image_path, parameters, to_json=True):
    """Makes predictions when all long running preparation operations are made. 
    Args:
        image_path (string): The path to the source image. 
        parameters (dict): The parameters produced by :func:`initialize`.
    Returns (Annotation):
        The annotation for the source image.
    """

    H = parameters['hypes']
    # print(parameters)
    # The default options for prediction of bounding boxes.
    # try:
    # options = H['evaluate']
    # except KeyError:
    #     pass

    # if 'pred_options' in parameters:
    #     # The new options for prediction of bounding boxes
    #     for key, val in parameters['pred_options'].items():
    #         options[key] = val

    # predict
    orig_img = imread(image_path)[:, :, :3]
    # img = Rotate90.do(orig_img) if 'rotate90' in H['data'] and H['data']['rotate90'] else orig_img
    img = orig_img
    img = imresize(img, (H['image_height'], H['image_width']), interp='cubic')
    np_pred_boxes, np_pred_confidences = parameters['sess']. \
        run([parameters['pred_boxes'], parameters['pred_confidences']], feed_dict={parameters['x_in']: img})

    image_info = {'path': image_path, 'original': orig_img, 'transformed': img}
    pred_anno = postprocess(image_info, np_pred_boxes, np_pred_confidences, H) #removed options as last arg
    result = [r.writeJSON() for r in pred_anno] if to_json else pred_anno
    return result


def postprocess(image_info, np_pred_boxes, np_pred_confidences, H, options={'min_conf':0.9, 'tau':0.25}):
    pred_anno = al.Annotation()
    pred_anno.imageName = image_info['path']
    pred_anno.imagePath = os.path.abspath(image_info['path'])
    _, rects = add_rectangles(H, [image_info['transformed']], np_pred_confidences, np_pred_boxes, use_stitching=False,
                              rnn_len=H['rnn_len'], min_conf=options['min_conf'], tau=options['tau'],
                              show_suppressed=False)

    rects = [r for r in rects if r.x1 < r.x2 and r.y1 < r.y2 and r.score > options['min_conf']]
    h, w = image_info['original'].shape[:2]
    if 'rotate90' in H['data'] and H['data']['rotate90']:
        # original image height is a width for roatated one
        rects = Rotate90.invert(h, rects)
    pred_anno.rects = rects
    pred_anno = rescale_boxes((H['image_height'], H['image_width']), pred_anno, h, w)
    return pred_anno


def prepare_options(hypes_path='hypes.json', options=None):
    """Sets parameters of the prediction process. If evaluate options provided partially, it'll merge them. 
    The priority is given to options argument to overwrite the same obtained from the hyperparameters file.
    Args:
        hypes_path (string): The path to model hyperparameters file.
        options (dict): The command line options to set before start predictions.
    Returns (dict):
        The model hyperparameters dictionary.
    """

    with open(hypes_path, 'r') as f:
        H = json.load(f)

    # set default options values if they were not provided
    if options is None:
        if 'evaluate' in H:
            options = H['evaluate']
        else:
            print ('Evaluate parameters were not found! You can provide them through hyperparameters json file '
                   'or hot_predict options parameter.')
            return None
    else:
        if 'evaluate' not in H:
            H['evaluate'] = {}
        # merge options argument into evaluate options from hyperparameters file
        for key, val in options.items():
            H['evaluate'][key] = val

    os.environ['CUDA_VISIBLE_DEVICES'] = str(H['evaluate']['gpu'])
    return H


def save_results(image_path, anno):
    """Saves results of the prediction.
    Args:
        image_path (string): The path to source image to predict bounding boxes.
        anno (Annotation): The predicted annotations for source image.
    Returns: 
        Nothing.
    """

    # draw
    new_img = Image.open(image_path)
    d = ImageDraw.Draw(new_img)
    rects = anno['rects'] if type(anno) is dict else anno.rects
    for r in rects:
        d.rectangle([r.left(), r.top(), r.right(), r.bottom()], outline=(255, 0, 0))

    # save
    fpath = os.path.join(os.path.dirname(image_path), 'result.png')
    new_img.save(fpath)
    subprocess.call(['chmod', '777', fpath])

    fpath = os.path.join(os.path.dirname(image_path), 'result.json')
    if type(anno) is dict:
        with open(fpath, 'w') as f:
            json.dump(anno, f)
    else:
        al.saveJSON(fpath, anno)
    subprocess.call(['chmod', '777', fpath])


def main():
    parser = OptionParser(usage='usage: %prog [options] <image> <weights> <hypes>')
    parser.add_option('--gpu', action='store', type='int', default=0)
    parser.add_option('--tau', action='store', type='float', default=0.25)
    parser.add_option('--min_conf', action='store', type='float', default=0.2)

    (options, args) = parser.parse_args()
    if len(args) < 3:
        print ('Provide image, weights and hypes paths')
        return

    init_params = initialize(args[1], args[2], options.__dict__)
    pred_anno = hot_predict(args[0], init_params, True)
    # test = pred_anno.printContent()
    print(pred_anno)
    test = pred_anno.writeJSON()
    # print('---------')
    print(test)

    for val in test:
        print('----')
        print(test[val])
        print(val)
        print('-----')

        list_count = 0
        if val == 'image_path':
            continue
        else:
            for item in test[val]:
                print('----------------')
                print(type(test[val][list_count]['score']))
                test[val][list_count]['score'] = float(test[val][list_count]['score'])
                list_count +=1




    with open('test.json','w') as f:
        json.dump(test, f)

    print('ARGS:')
    print(args[0])
    # print(test)

    # save_results(args[0], pred_anno)


if __name__ == '__main__':
    main()