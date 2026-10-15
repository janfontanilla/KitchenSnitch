#!/usr/bin/env python3
"""Draw the fridge, sink and faucet zones on a photo of the kitchen.

Usage:
    python3 scripts/calibrate_zones.py kitchen.jpg
    python3 scripts/calibrate_zones.py --camera 0       # grab a frame from a webcam

For each zone, drag a rectangle and press ENTER (or SPACE). Press C to cancel.
Writes src/kitchensnitch_bringup/config/zones.yaml.
"""
import argparse
import sys
from pathlib import Path

import cv2

OUT = Path(__file__).resolve().parent.parent / 'src/kitchensnitch_bringup/config/zones.yaml'
ZONES = ['fridge', 'sink', 'faucet']


def load_frame(args):
    if args.camera is not None:
        cap = cv2.VideoCapture(args.camera)
        for _ in range(10):  # let auto exposure settle
            ok, frame = cap.read()
        cap.release()
        if not ok:
            sys.exit('Could not read from the camera')
        return frame
    frame = cv2.imread(args.image)
    if frame is None:
        sys.exit(f'Could not read image: {args.image}')
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('image', nargs='?', help='Photo of the kitchen from the camera position')
    parser.add_argument('--camera', type=int, help='Webcam index to grab a frame from instead')
    args = parser.parse_args()
    if args.image is None and args.camera is None:
        parser.error('give an image path or --camera N')

    frame = load_frame(args)
    h, w = frame.shape[:2]
    zones = {}
    for name in ZONES:
        x, y, rw, rh = cv2.selectROI(f'Draw the {name} zone, then press ENTER', frame, False)
        cv2.destroyAllWindows()
        if rw == 0 or rh == 0:
            sys.exit(f'No {name} zone drawn, nothing written')
        zones[name] = [round(x / w, 3), round(y / h, 3), round(rw / w, 3), round(rh / h, 3)]

    OUT.write_text(
        '# Normalized [x, y, w, h] zones. Written by scripts/calibrate_zones.py\n'
        'pitcher_tracker:\n  ros__parameters:\n'
        f'    fridge_zone: {zones["fridge"]}\n    sink_zone: {zones["sink"]}\n'
        'sink_checker:\n  ros__parameters:\n'
        f'    sink_zone: {zones["sink"]}\n'
        'faucet_watcher:\n  ros__parameters:\n'
        f'    faucet_zone: {zones["faucet"]}\n',
        encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
