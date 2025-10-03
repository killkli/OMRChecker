import os
from collections import defaultdict
from typing import Any

import cv2
import matplotlib.pyplot as plt
import numpy as np

import src.constants as constants
from src.logger import logger

try:
    qr_detector = cv2.QRCodeDetector()
except AttributeError:
    logger.warning("OpenCV QRCodeDetector not available. Install OpenCV >= 4.5.0 for QR support.")
    qr_detector = None
from src.utils.image import CLAHE_HELPER, ImageUtils
from src.utils.interaction import InteractionUtils


class ImageInstanceOps:
    """Class to hold fine-tuned utilities for a group of images. One instance for each processing directory."""

    save_img_list: Any = defaultdict(list)

    def __init__(self, tuning_config):
        super().__init__()
        self.tuning_config = tuning_config
        self.save_image_level = tuning_config.outputs.save_image_level

    def apply_preprocessors(self, file_path, in_omr, template):
        tuning_config = self.tuning_config
        # resize to conform to template
        in_omr = ImageUtils.resize_util(
            in_omr,
            tuning_config.dimensions.processing_width,
            tuning_config.dimensions.processing_height,
        )

        self.transform_matrix = None
        # run pre_processors in sequence
        for pre_processor in template.pre_processors:
            result = pre_processor.apply_filter(in_omr, file_path)
            if isinstance(result, tuple):
                in_omr, transform_matrix = result
                if hasattr(pre_processor, 'transform_matrix'):
                    self.transform_matrix = pre_processor.transform_matrix
            else:
                in_omr = result
        return in_omr

    def read_omr_response(self, template, image, raw_image, name, save_dir=None):
        config = self.tuning_config
        auto_align = config.alignment_params.auto_align
        try:
            img = image.copy()
            # origDim = img.shape[:2]
            img = ImageUtils.resize_util(
                img, template.page_dimensions[0], template.page_dimensions[1]
            )
            if img.max() > img.min():
                img = ImageUtils.normalize_util(img)

            if self.transform_matrix is not None:
                logger.info("Transform matrix shape: %s", self.transform_matrix.shape)
                logger.info("Applying perspective transform to template points using homography")
                qr_origins_before = []
                for fb in template.field_blocks:
                    if fb.name == 'QR_Code' or fb.field_type == 'QTYPE_CUSTOM':
                        qr_origins_before.append((fb.name, fb.origin.copy()))
                    # Transform origin
                    origin_pts = np.array([[[fb.origin[0], fb.origin[1]]]], dtype=np.float32)
                    trans_origin = cv2.perspectiveTransform(origin_pts, self.transform_matrix)
                    fb.origin = [int(trans_origin[0][0][0]), int(trans_origin[0][0][1])]

                    # Transform bubble points
                    for strip in fb.traverse_bubbles:
                        for bubble in strip:
                            pt = np.array([[[bubble.x, bubble.y]]], dtype=np.float32)
                            trans_pt = cv2.perspectiveTransform(pt, self.transform_matrix)
                            bubble.x = int(trans_pt[0][0][0])
                            bubble.y = int(trans_pt[0][0][1])
                logger.info("QR blocks before transform: %s", qr_origins_before)
                for name, origin in qr_origins_before:
                    # Find the QR field_block and log after
                    for fb in template.field_blocks:
                        if fb.name == name or (hasattr(fb, 'field_type') and fb.field_type == 'QTYPE_CUSTOM'):
                            logger.info("QR block %s transformed origin: %s (was %s)", name, fb.origin, origin)

            # Processing copies
            transp_layer = img.copy()
            final_marked = img.copy()

            morph = img.copy()
            self.append_save_img(3, morph)

            if auto_align:
                # Note: clahe is good for morphology, bad for thresholding
                morph = CLAHE_HELPER.apply(morph)
                self.append_save_img(3, morph)
                # Remove shadows further, make columns/boxes darker (less gamma)
                morph = ImageUtils.adjust_gamma(
                    morph, config.threshold_params.GAMMA_LOW
                )
                # TODO: all numbers should come from either constants or config
                _, morph = cv2.threshold(morph, 220, 220, cv2.THRESH_TRUNC)
                morph = ImageUtils.normalize_util(morph)
                self.append_save_img(3, morph)
                if config.outputs.show_image_level >= 4:
                    InteractionUtils.show("morph1", morph, 0, 1, config)

            # Move them to data class if needed
            # Overlay Transparencies
            alpha = 0.65
            omr_response = {}
            multi_marked, multi_roll = 0, 0

            # TODO Make this part useful for visualizing status checks
            # blackVals=[0]
            # whiteVals=[255]

            if config.outputs.show_image_level >= 5:
                all_c_box_vals = {"int": [], "mcq": []}
                # TODO: simplify this logic
                q_nums = {"int": [], "mcq": []}

            # Find Shifts for the field_blocks --> Before calculating threshold!
            if auto_align:
                # print("Begin Alignment")
                # Open : erode then dilate
                v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 10))
                morph_v = cv2.morphologyEx(
                    morph, cv2.MORPH_OPEN, v_kernel, iterations=3
                )
                _, morph_v = cv2.threshold(morph_v, 200, 200, cv2.THRESH_TRUNC)
                morph_v = 255 - ImageUtils.normalize_util(morph_v)

                if config.outputs.show_image_level >= 3:
                    InteractionUtils.show(
                        "morphed_vertical", morph_v, 0, 1, config=config
                    )

                # InteractionUtils.show("morph1",morph,0,1,config=config)
                # InteractionUtils.show("morphed_vertical",morph_v,0,1,config=config)

                self.append_save_img(3, morph_v)

                morph_thr = 60  # for Mobile images, 40 for scanned Images
                _, morph_v = cv2.threshold(morph_v, morph_thr, 255, cv2.THRESH_BINARY)
                # kernel best tuned to 5x5 now
                morph_v = cv2.erode(morph_v, np.ones((5, 5), np.uint8), iterations=2)

                self.append_save_img(3, morph_v)
                # h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 2))
                # morph_h = cv2.morphologyEx(morph, cv2.MORPH_OPEN, h_kernel, iterations=3)
                # ret, morph_h = cv2.threshold(morph_h,200,200,cv2.THRESH_TRUNC)
                # morph_h = 255 - normalize_util(morph_h)
                # InteractionUtils.show("morph_h",morph_h,0,1,config=config)
                # _, morph_h = cv2.threshold(morph_h,morph_thr,255,cv2.THRESH_BINARY)
                # morph_h = cv2.erode(morph_h,  np.ones((5,5),np.uint8), iterations = 2)
                if config.outputs.show_image_level >= 3:
                    InteractionUtils.show(
                        "morph_thr_eroded", morph_v, 0, 1, config=config
                    )

                self.append_save_img(6, morph_v)

                # template relative alignment code
                for field_block in template.field_blocks:
                    s, d = field_block.origin, field_block.dimensions

                    match_col, max_steps, align_stride, thk = map(
                        config.alignment_params.get,
                        [
                            "match_col",
                            "max_steps",
                            "stride",
                            "thickness",
                        ],
                    )
                    shift, steps = 0, 0
                    while steps < max_steps:
                        left_mean = np.mean(
                            morph_v[
                                s[1] : s[1] + d[1],
                                s[0] + shift - thk : -thk + s[0] + shift + match_col,
                            ]
                        )
                        right_mean = np.mean(
                            morph_v[
                                s[1] : s[1] + d[1],
                                s[0]
                                + shift
                                - match_col
                                + d[0]
                                + thk : thk
                                + s[0]
                                + shift
                                + d[0],
                            ]
                        )

                        # For demonstration purposes-
                        # if(field_block.name == "int1"):
                        #     ret = morph_v.copy()
                        #     cv2.rectangle(ret,
                        #                   (s[0]+shift-thk,s[1]),
                        #                   (s[0]+shift+thk+d[0],s[1]+d[1]),
                        #                   constants.CLR_WHITE,
                        #                   3)
                        #     appendSaveImg(6,ret)
                        # print(shift, left_mean, right_mean)
                        left_shift, right_shift = left_mean > 100, right_mean > 100
                        if left_shift:
                            if right_shift:
                                break
                            else:
                                shift -= align_stride
                        else:
                            if right_shift:
                                shift += align_stride
                            else:
                                break
                        steps += 1

                    field_block.shift = shift
                    # print("Aligned field_block: ",field_block.name,"Corrected Shift:",
                    #   field_block.shift,", dimensions:", field_block.dimensions,
                    #   "origin:", field_block.origin,'\n')
                # print("End Alignment")

            final_align = None
            if config.outputs.show_image_level >= 2:
                initial_align = self.draw_template_layout(img, template, shifted=False)
                final_align = self.draw_template_layout(
                    img, template, shifted=True, draw_qvals=True
                )
                # appendSaveImg(4,mean_vals)
                self.append_save_img(2, initial_align)
                self.append_save_img(2, final_align)

                if auto_align:
                    final_align = np.hstack((initial_align, final_align))
            self.append_save_img(5, img)

            # Get mean bubbleValues n other stats
            all_q_vals, all_q_strip_arrs, all_q_std_vals = [], [], []
            total_q_strip_no = 0
            for field_block in template.field_blocks:
                box_w, box_h = field_block.bubble_dimensions
                q_std_vals = []
                for field_block_bubbles in field_block.traverse_bubbles:
                    q_strip_vals = []
                    for pt in field_block_bubbles:
                        # shifted
                        x, y = (pt.x + field_block.shift, pt.y)
                        rect = [y, y + box_h, x, x + box_w]
                        q_strip_vals.append(
                            cv2.mean(img[rect[0] : rect[1], rect[2] : rect[3]])[0]
                            # detectCross(img, rect) ? 100 : 0
                        )
                    q_std_vals.append(round(np.std(q_strip_vals), 2))
                    all_q_strip_arrs.append(q_strip_vals)
                    # _, _, _ = get_global_threshold(q_strip_vals, "QStrip Plot",
                    #   plot_show=False, sort_in_plot=True)
                    # hist = getPlotImg()
                    # InteractionUtils.show("QStrip "+field_block_bubbles[0].field_label, hist, 0, 1,config=config)
                    all_q_vals.extend(q_strip_vals)
                    # print(total_q_strip_no, field_block_bubbles[0].field_label, q_std_vals[len(q_std_vals)-1])
                    total_q_strip_no += 1
                all_q_std_vals.extend(q_std_vals)

            global_std_thresh, _, _ = self.get_global_threshold(
                all_q_std_vals
            )  # , "Q-wise Std-dev Plot", plot_show=True, sort_in_plot=True)
            # plt.show()
            # hist = getPlotImg()
            # InteractionUtils.show("StdHist", hist, 0, 1,config=config)

            # Note: Plotting takes Significant times here --> Change Plotting args
            # to support show_image_level
            # , "Mean Intensity Histogram",plot_show=True, sort_in_plot=True)
            global_thr, _, _ = self.get_global_threshold(all_q_vals, looseness=4)

            logger.info(
                f"Thresholding: \tglobal_thr: {round(global_thr, 2)} \tglobal_std_THR: {round(global_std_thresh, 2)}\t{'(Looks like a Xeroxed OMR)' if (global_thr == 255) else ''}"
            )
            # plt.show()
            # hist = getPlotImg()
            # InteractionUtils.show("StdHist", hist, 0, 1,config=config)

            # if(config.outputs.show_image_level>=1):
            #     hist = getPlotImg()
            #     InteractionUtils.show("Hist", hist, 0, 1,config=config)
            #     appendSaveImg(4,hist)
            #     appendSaveImg(5,hist)
            #     appendSaveImg(2,hist)

            per_omr_threshold_avg, total_q_strip_no, total_q_box_no = 0, 0, 0
            for field_block in template.field_blocks:
                # Check for QR block: no fieldType, single bubbleValue as placeholder
                # Handle QR blocks: prioritize field_type=='QTYPE_CUSTOM', fallback to name=='QR_Code' with bubble_values
                if hasattr(field_block, 'field_type') and field_block.field_type == "QTYPE_CUSTOM":
                    # Handle QR code decoding
                    if qr_detector is None:
                        logger.warning("QR detector not available, skipping QR field")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = field_block.empty_val
                        continue

                    # Log QR block details
                    logger.info(f"QR Block after transform: name={field_block.name}, origin={field_block.origin}, shift={getattr(field_block, 'shift', 0)}, bubble_dims={field_block.bubble_dimensions}")

                    # Get QR region
                    box_w, box_h = field_block.bubble_dimensions
                    x, y = field_block.origin[0] + shift, field_block.origin[1]
                    qr_size = max(box_w, box_h) * 50  # Even larger padding to cover full QR
                    logger.info(f"Extracting QR region from warped img: x={x}, y={y}, qr_size={qr_size}")
                    qr_region = img[max(0, y - qr_size//2):y + qr_size//2, max(0, x - qr_size//2):x + qr_size//2]
                    logger.info(f"QR region: x={x}, y={y}, size={qr_size}, shape={qr_region.shape}, mean_intensity={np.mean(qr_region):.2f}")
                    if qr_region.size == 0:
                        qr_region = img[y:y+box_h, x:x+box_w]
                        logger.warning(f"Fallback QR region shape: {qr_region.shape}, mean={np.mean(qr_region):.2f}")

                    # Decode QR (convert to grayscale for better detection)
                    if len(qr_region.shape) == 3:
                        qr_gray = cv2.cvtColor(qr_region, cv2.COLOR_BGR2GRAY)
                    else:
                        qr_gray = qr_region

                    logger.info(f"QR gray region shape: {qr_gray.shape}, dtype: {qr_gray.dtype}")

                    # Try detectAndDecode (returns decoded_string, points, straight_qrcode)
                    decoded_info, points, straight_qrcode = qr_detector.detectAndDecode(qr_gray)

                    # Debug: log raw return values
                    logger.info(f"QR detectAndDecode: decoded_info type={type(decoded_info)}, len={len(decoded_info) if isinstance(decoded_info, str) else 'N/A'}")
                    logger.info(f"QR decoded_info content: {decoded_info[:100] if isinstance(decoded_info, str) and len(decoded_info) > 0 else decoded_info}")
                    if points is not None and hasattr(points, 'shape'):
                        logger.info(f"QR detector returned points with shape: {points.shape}, dtype: {points.dtype}")

                    # Check if QR was successfully decoded (decoded_info should be a string)
                    decoded_success = isinstance(decoded_info, str) and len(decoded_info) > 0

                    if not decoded_success:
                        logger.warning(f"QR detection failed or returned empty string. Region shape: {qr_region.shape}, mean: {np.mean(qr_region):.2f}")

                    if decoded_success:
                        decoded_data = str(decoded_info).strip()
                        logger.info(f"QR decoded: {decoded_data}")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = decoded_data
                        # Draw on final_marked - only if points are valid QR corners (4 points)
                        if points is not None and points.size > 0:
                            # QR detector should return 4 corner points with shape (1, 4, 2) or (4, 2)
                            if points.shape == (1, 4, 2):
                                # Already correct shape for cv2.polylines
                                points_to_draw = points[0].reshape((-1, 1, 2)).astype(np.int32)
                                # Adjust coordinates to full image (add offset from qr_region extraction)
                                offset_x = max(0, x - qr_size//2)
                                offset_y = max(0, y - qr_size//2)
                                points_to_draw[:, :, 0] += offset_x
                                points_to_draw[:, :, 1] += offset_y
                                cv2.polylines(final_marked, [points_to_draw], True, constants.CLR_DARK_GRAY, 3)
                                cv2.putText(final_marked, decoded_data[:10] + "...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            elif points.shape == (4, 2):
                                points_to_draw = points.reshape((-1, 1, 2)).astype(np.int32)
                                offset_x = max(0, x - qr_size//2)
                                offset_y = max(0, y - qr_size//2)
                                points_to_draw[:, :, 0] += offset_x
                                points_to_draw[:, :, 1] += offset_y
                                cv2.polylines(final_marked, [points_to_draw], True, constants.CLR_DARK_GRAY, 3)
                                cv2.putText(final_marked, decoded_data[:10] + "...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            else:
                                logger.warning(f"Unexpected QR points shape: {points.shape}, skipping drawing")
                    else:
                        logger.warning("No QR code detected")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = field_block.empty_val
                    continue

                elif len(field_block.bubble_values) == 1 and field_block.name == "QR_Code":
                    # Fallback for no field_type QR block
                    if qr_detector is None:
                        logger.warning("QR detector not available, skipping QR field")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = field_block.empty_val
                        continue

                    # Get QR region
                    box_w, box_h = field_block.bubble_dimensions
                    shift = getattr(field_block, 'shift', 0)
                    s = field_block.origin
                    x, y = s[0] + shift, s[1]
                    qr_size = max(box_w, box_h) * 20
                    qr_region = img[max(0, y - qr_size//2):y + qr_size//2, max(0, x - qr_size//2):x + qr_size//2]
                    if qr_region.size == 0:
                        qr_region = img[y:y+box_h, x:x+box_w]

                    # Decode QR (returns decoded_string, points, straight_qrcode)
                    decoded_info, points, straight_qrcode = qr_detector.detectAndDecode(qr_region)
                    logger.info(f"QR decoded_info: {decoded_info[:100] if isinstance(decoded_info, str) and len(decoded_info) > 0 else decoded_info}")
                    if points is not None and hasattr(points, 'shape'):
                        logger.info(f"QR detector returned points with shape: {points.shape}")
                    # Check if QR was successfully decoded (should be non-empty string)
                    decoded_success = isinstance(decoded_info, str) and len(decoded_info) > 0
                    if decoded_success:
                        decoded_data = str(decoded_info).strip()
                        logger.info(f"QR decoded: {decoded_data}")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = decoded_data
                        # Draw on final_marked - only if points are valid QR corners
                        if points is not None and points.size > 0:
                            if points.shape == (1, 4, 2):
                                points_to_draw = points[0].reshape((-1, 1, 2)).astype(np.int32)
                                offset_x = max(0, x - qr_size//2)
                                offset_y = max(0, y - qr_size//2)
                                points_to_draw[:, :, 0] += offset_x
                                points_to_draw[:, :, 1] += offset_y
                                cv2.polylines(final_marked, [points_to_draw], True, constants.CLR_DARK_GRAY, 3)
                                cv2.putText(final_marked, decoded_data[:10] + "...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            elif points.shape == (4, 2):
                                points_to_draw = points.reshape((-1, 1, 2)).astype(np.int32)
                                offset_x = max(0, x - qr_size//2)
                                offset_y = max(0, y - qr_size//2)
                                points_to_draw[:, :, 0] += offset_x
                                points_to_draw[:, :, 1] += offset_y
                                cv2.polylines(final_marked, [points_to_draw], True, constants.CLR_DARK_GRAY, 3)
                                cv2.putText(final_marked, decoded_data[:10] + "...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            else:
                                logger.warning(f"Unexpected QR points shape: {points.shape}, skipping drawing")
                    else:
                        logger.warning("No QR code detected")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = field_block.empty_val
                    continue

                if hasattr(field_block, 'field_type') and field_block.field_type == "QTYPE_CUSTOM":
                    # Handle QR code decoding
                    if qr_detector is None:
                        logger.warning("QR detector not available, skipping QR field")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = field_block.empty_val
                        continue

                    # Get QR region
                    box_w, box_h = field_block.bubble_dimensions
                    shift = getattr(field_block, 'shift', 0)
                    s = field_block.origin
                    x, y = s[0] + shift, s[1]
                    qr_size = max(box_w, box_h) * 20
                    qr_region = img[max(0, y - qr_size//2):y + qr_size//2, max(0, x - qr_size//2):x + qr_size//2]
                    if qr_region.size == 0:
                        qr_region = img[y:y+box_h, x:x+box_w]

                    # Decode QR (returns decoded_string, points, straight_qrcode)
                    decoded_info, points, straight_qrcode = qr_detector.detectAndDecode(qr_region)
                    logger.info(f"QR decoded_info: {decoded_info[:100] if isinstance(decoded_info, str) and len(decoded_info) > 0 else decoded_info}")
                    if points is not None and hasattr(points, 'shape'):
                        logger.info(f"QR detector returned points with shape: {points.shape}")
                    # Check if QR was successfully decoded (should be non-empty string)
                    decoded_success = isinstance(decoded_info, str) and len(decoded_info) > 0
                    if decoded_success:
                        decoded_data = str(decoded_info).strip()
                        logger.info(f"QR decoded: {decoded_data}")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = decoded_data
                        # Draw on final_marked - only if points are valid QR corners
                        if points is not None and points.size > 0:
                            if points.shape == (1, 4, 2):
                                points_to_draw = points[0].reshape((-1, 1, 2)).astype(np.int32)
                                offset_x = max(0, x - qr_size//2)
                                offset_y = max(0, y - qr_size//2)
                                points_to_draw[:, :, 0] += offset_x
                                points_to_draw[:, :, 1] += offset_y
                                cv2.polylines(final_marked, [points_to_draw], True, constants.CLR_DARK_GRAY, 3)
                                cv2.putText(final_marked, decoded_data[:10] + "...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            elif points.shape == (4, 2):
                                points_to_draw = points.reshape((-1, 1, 2)).astype(np.int32)
                                offset_x = max(0, x - qr_size//2)
                                offset_y = max(0, y - qr_size//2)
                                points_to_draw[:, :, 0] += offset_x
                                points_to_draw[:, :, 1] += offset_y
                                cv2.polylines(final_marked, [points_to_draw], True, constants.CLR_DARK_GRAY, 3)
                                cv2.putText(final_marked, decoded_data[:10] + "...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            else:
                                logger.warning(f"Unexpected QR points shape: {points.shape}, skipping drawing")
                    else:
                        logger.warning("No QR code detected")
                        field_label = field_block.field_labels[0] if field_block.field_labels else "qr_id"
                        omr_response[field_label] = field_block.empty_val
                    continue

                block_q_strip_no = 1
                box_w, box_h = field_block.bubble_dimensions
                shift = field_block.shift
                s, d = field_block.origin, field_block.dimensions
                key = field_block.name[:3]
                # cv2.rectangle(final_marked,(s[0]+shift,s[1]),(s[0]+shift+d[0],
                #   s[1]+d[1]),CLR_BLACK,3)
                for field_block_bubbles in field_block.traverse_bubbles:
                    # All Black or All White case
                    no_outliers = all_q_std_vals[total_q_strip_no] < global_std_thresh
                    # print(total_q_strip_no, field_block_bubbles[0].field_label,
                    #   all_q_std_vals[total_q_strip_no], "no_outliers:", no_outliers)
                    per_q_strip_threshold = self.get_local_threshold(
                        all_q_strip_arrs[total_q_strip_no],
                        global_thr,
                        no_outliers,
                        f"Mean Intensity Histogram for {key}.{field_block_bubbles[0].field_label}.{block_q_strip_no}",
                        config.outputs.show_image_level >= 6,
                    )
                    # print(field_block_bubbles[0].field_label,key,block_q_strip_no, "THR: ",
                    #   round(per_q_strip_threshold,2))
                    per_omr_threshold_avg += per_q_strip_threshold

                    # Note: Little debugging visualization - view the particular Qstrip
                    # if(
                    #     0
                    #     # or "q17" in (field_block_bubbles[0].field_label)
                    #     # or (field_block_bubbles[0].field_label+str(block_q_strip_no))=="q15"
                    #  ):
                    #     st, end = qStrip
                    #     InteractionUtils.show("QStrip: "+key+"-"+str(block_q_strip_no),
                    #     img[st[1] : end[1], st[0]+shift : end[0]+shift],0,config=config)

                    # TODO: get rid of total_q_box_no
                    detected_bubbles = []
                    for bubble in field_block_bubbles:
                        bubble_is_marked = (
                            per_q_strip_threshold > all_q_vals[total_q_box_no]
                        )
                        total_q_box_no += 1
                        if bubble_is_marked:
                            detected_bubbles.append(bubble)
                            x, y, field_value = (
                                bubble.x + field_block.shift,
                                bubble.y,
                                bubble.field_value,
                            )
                            cv2.rectangle(
                                final_marked,
                                (int(x + box_w / 12), int(y + box_h / 12)),
                                (
                                    int(x + box_w - box_w / 12),
                                    int(y + box_h - box_h / 12),
                                ),
                                constants.CLR_DARK_GRAY,
                                3,
                            )

                            cv2.putText(
                                final_marked,
                                str(field_value),
                                (x, y),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                constants.TEXT_SIZE,
                                (20, 20, 10),
                                int(1 + 3.5 * constants.TEXT_SIZE),
                            )
                        else:
                            cv2.rectangle(
                                final_marked,
                                (int(x + box_w / 10), int(y + box_h / 10)),
                                (
                                    int(x + box_w - box_w / 10),
                                    int(y + box_h - box_h / 10),
                                ),
                                constants.CLR_GRAY,
                                -1,
                            )

                    for bubble in detected_bubbles:
                        field_label, field_value = (
                            bubble.field_label,
                            bubble.field_value,
                        )
                        # Only send rolls multi-marked in the directory
                        multi_marked_local = field_label in omr_response
                        omr_response[field_label] = (
                            (omr_response[field_label] + field_value)
                            if multi_marked_local
                            else field_value
                        )
                        # TODO: generalize this into identifier
                        # multi_roll = multi_marked_local and "Roll" in str(q)
                        multi_marked = multi_marked or multi_marked_local

                    if len(detected_bubbles) == 0:
                        field_label = field_block_bubbles[0].field_label
                        omr_response[field_label] = field_block.empty_val

                    if config.outputs.show_image_level >= 5:
                        if key in all_c_box_vals:
                            q_nums[key].append(f"{key[:2]}_c{str(block_q_strip_no)}")
                            all_c_box_vals[key].append(
                                all_q_strip_arrs[total_q_strip_no]
                            )

                    block_q_strip_no += 1
                    total_q_strip_no += 1
                # /for field_block

            per_omr_threshold_avg /= total_q_strip_no
            per_omr_threshold_avg = round(per_omr_threshold_avg, 2)
            # Translucent
            cv2.addWeighted(
                final_marked, alpha, transp_layer, 1 - alpha, 0, final_marked
            )
            # Box types
            if config.outputs.show_image_level >= 6:
                # plt.draw()
                f, axes = plt.subplots(len(all_c_box_vals), sharey=True)
                f.canvas.manager.set_window_title(name)
                ctr = 0
                type_name = {
                    "int": "Integer",
                    "mcq": "MCQ",
                    "med": "MED",
                    "rol": "Roll",
                }
                for k, boxvals in all_c_box_vals.items():
                    axes[ctr].title.set_text(type_name[k] + " Type")
                    axes[ctr].boxplot(boxvals)
                    # thrline=axes[ctr].axhline(per_omr_threshold_avg,color='red',ls='--')
                    # thrline.set_label("Average THR")
                    axes[ctr].set_ylabel("Intensity")
                    axes[ctr].set_xticklabels(q_nums[k])
                    # axes[ctr].legend()
                    ctr += 1
                # imshow will do the waiting
                plt.tight_layout(pad=0.5)
                plt.show()

            if config.outputs.show_image_level >= 3 and final_align is not None:
                final_align = ImageUtils.resize_util_h(
                    final_align, int(config.dimensions.display_height)
                )
                # [final_align.shape[1],0])
                InteractionUtils.show(
                    "Template Alignment Adjustment", final_align, 0, 0, config=config
                )

            if config.outputs.save_detections and save_dir is not None:
                if multi_roll:
                    save_dir = save_dir.joinpath("_MULTI_")
                image_path = str(save_dir.joinpath(name))
                ImageUtils.save_img(image_path, final_marked)

            self.append_save_img(2, final_marked)

            if save_dir is not None:
                for i in range(config.outputs.save_image_level):
                    self.save_image_stacks(i + 1, name, save_dir)

            return omr_response, final_marked, multi_marked, multi_roll

        except Exception as e:
            raise e

    @staticmethod
    def draw_template_layout(img, template, shifted=True, draw_qvals=False, border=-1):
        img = ImageUtils.resize_util(
            img, template.page_dimensions[0], template.page_dimensions[1]
        )
        final_align = img.copy()
        for field_block in template.field_blocks:
            s, d = field_block.origin, field_block.dimensions
            box_w, box_h = field_block.bubble_dimensions
            shift = field_block.shift
            if shifted:
                cv2.rectangle(
                    final_align,
                    (s[0] + shift, s[1]),
                    (s[0] + shift + d[0], s[1] + d[1]),
                    constants.CLR_BLACK,
                    3,
                )
            else:
                cv2.rectangle(
                    final_align,
                    (s[0], s[1]),
                    (s[0] + d[0], s[1] + d[1]),
                    constants.CLR_BLACK,
                    3,
                )
            for field_block_bubbles in field_block.traverse_bubbles:
                for pt in field_block_bubbles:
                    x, y = (pt.x + field_block.shift, pt.y) if shifted else (pt.x, pt.y)
                    cv2.rectangle(
                        final_align,
                        (int(x + box_w / 10), int(y + box_h / 10)),
                        (int(x + box_w - box_w / 10), int(y + box_h - box_h / 10)),
                        constants.CLR_GRAY,
                        border,
                    )
                    if draw_qvals:
                        rect = [y, y + box_h, x, x + box_w]
                        cv2.putText(
                            final_align,
                            f"{int(cv2.mean(img[rect[0] : rect[1], rect[2] : rect[3]])[0])}",
                            (rect[2] + 2, rect[0] + (box_h * 2) // 3),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            constants.CLR_BLACK,
                            2,
                        )
            if shifted:
                text_in_px = cv2.getTextSize(
                    field_block.name, cv2.FONT_HERSHEY_SIMPLEX, constants.TEXT_SIZE, 4
                )
                cv2.putText(
                    final_align,
                    field_block.name,
                    (int(s[0] + d[0] - text_in_px[0][0]), int(s[1] - text_in_px[0][1])),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    constants.TEXT_SIZE,
                    constants.CLR_BLACK,
                    4,
                )
        return final_align

    def get_global_threshold(
        self,
        q_vals_orig,
        plot_title=None,
        plot_show=True,
        sort_in_plot=True,
        looseness=1,
    ):
        """
        Note: Cannot assume qStrip has only-gray or only-white bg
            (in which case there is only one jump).
        So there will be either 1 or 2 jumps.
        1 Jump :
                ......
                ||||||
                ||||||  <-- risky THR
                ||||||  <-- safe THR
            ....||||||
            ||||||||||

        2 Jumps :
                ......
                |||||| <-- wrong THR
            ....||||||
            |||||||||| <-- safe THR
            ..||||||||||
            ||||||||||||

        The abstract "First LARGE GAP" is perfect for this.
        Current code is considering ONLY TOP 2 jumps(>= MIN_GAP) to be big,
            gives the smaller one

        """
        config = self.tuning_config
        PAGE_TYPE_FOR_THRESHOLD, MIN_JUMP, JUMP_DELTA = map(
            config.threshold_params.get,
            [
                "PAGE_TYPE_FOR_THRESHOLD",
                "MIN_JUMP",
                "JUMP_DELTA",
            ],
        )

        global_default_threshold = (
            constants.GLOBAL_PAGE_THRESHOLD_WHITE
            if PAGE_TYPE_FOR_THRESHOLD == "white"
            else constants.GLOBAL_PAGE_THRESHOLD_BLACK
        )

        # Sort the Q bubbleValues
        # TODO: Change var name of q_vals
        q_vals = sorted(q_vals_orig)
        # Find the FIRST LARGE GAP and set it as threshold:
        ls = (looseness + 1) // 2
        l = len(q_vals) - ls
        max1, thr1 = MIN_JUMP, global_default_threshold
        for i in range(ls, l):
            jump = q_vals[i + ls] - q_vals[i - ls]
            if jump > max1:
                max1 = jump
                thr1 = q_vals[i - ls] + jump / 2

        # NOTE: thr2 is deprecated, thus is JUMP_DELTA
        # Make use of the fact that the JUMP_DELTA(Vertical gap ofc) between
        # values at detected jumps would be atleast 20
        max2, thr2 = MIN_JUMP, global_default_threshold
        # Requires atleast 1 gray box to be present (Roll field will ensure this)
        for i in range(ls, l):
            jump = q_vals[i + ls] - q_vals[i - ls]
            new_thr = q_vals[i - ls] + jump / 2
            if jump > max2 and abs(thr1 - new_thr) > JUMP_DELTA:
                max2 = jump
                thr2 = new_thr
        # global_thr = min(thr1,thr2)
        global_thr, j_low, j_high = thr1, thr1 - max1 // 2, thr1 + max1 // 2

        # # For normal images
        # thresholdRead =  116
        # if(thr1 > thr2 and thr2 > thresholdRead):
        #     print("Note: taking safer thr line.")
        #     global_thr, j_low, j_high = thr2, thr2 - max2//2, thr2 + max2//2

        if plot_title:
            _, ax = plt.subplots()
            ax.bar(range(len(q_vals_orig)), q_vals if sort_in_plot else q_vals_orig)
            ax.set_title(plot_title)
            thrline = ax.axhline(global_thr, color="green", ls="--", linewidth=5)
            thrline.set_label("Global Threshold")
            thrline = ax.axhline(thr2, color="red", ls=":", linewidth=3)
            thrline.set_label("THR2 Line")
            # thrline=ax.axhline(j_low,color='red',ls='-.', linewidth=3)
            # thrline=ax.axhline(j_high,color='red',ls='-.', linewidth=3)
            # thrline.set_label("Boundary Line")
            # ax.set_ylabel("Mean Intensity")
            ax.set_ylabel("Values")
            ax.set_xlabel("Position")
            ax.legend()
            if plot_show:
                plt.title(plot_title)
                plt.show()

        return global_thr, j_low, j_high

    def get_local_threshold(
        self, q_vals, global_thr, no_outliers, plot_title=None, plot_show=True
    ):
        """
        TODO: Update this documentation too-
        //No more - Assumption : Colwise background color is uniformly gray or white,
                but not alternating. In this case there is atmost one jump.

        0 Jump :
                        <-- safe THR?
            .......
            ...|||||||
            ||||||||||  <-- safe THR?
        // How to decide given range is above or below gray?
            -> global q_vals shall absolutely help here. Just run same function
                on total q_vals instead of colwise _//
        How to decide it is this case of 0 jumps

        1 Jump :
                ......
                ||||||
                ||||||  <-- risky THR
                ||||||  <-- safe THR
            ....||||||
            ||||||||||

        """
        config = self.tuning_config
        # Sort the Q bubbleValues
        q_vals = sorted(q_vals)

        # Small no of pts cases:
        # base case: 1 or 2 pts
        if len(q_vals) < 3:
            thr1 = (
                global_thr
                if np.max(q_vals) - np.min(q_vals) < config.threshold_params.MIN_GAP
                else np.mean(q_vals)
            )
        else:
            # qmin, qmax, qmean, qstd = round(np.min(q_vals),2), round(np.max(q_vals),2),
            #   round(np.mean(q_vals),2), round(np.std(q_vals),2)
            # GVals = [round(abs(q-qmean),2) for q in q_vals]
            # gmean, gstd = round(np.mean(GVals),2), round(np.std(GVals),2)
            # # DISCRETION: Pretty critical factor in reading response
            # # Doesn't work well for small number of values.
            # DISCRETION = 2.7 # 2.59 was closest hit, 3.0 is too far
            # L2MaxGap = round(max([abs(g-gmean) for g in GVals]),2)
            # if(L2MaxGap > DISCRETION*gstd):
            #     no_outliers = False

            # # ^Stackoverflow method
            # print(field_label, no_outliers,"qstd",round(np.std(q_vals),2), "gstd", gstd,
            #   "Gaps in gvals",sorted([round(abs(g-gmean),2) for g in GVals],reverse=True),
            #   '\t',round(DISCRETION*gstd,2), L2MaxGap)

            # else:
            # Find the LARGEST GAP and set it as threshold: //(FIRST LARGE GAP)
            l = len(q_vals) - 1
            max1, thr1 = config.threshold_params.MIN_JUMP, 255
            for i in range(1, l):
                jump = q_vals[i + 1] - q_vals[i - 1]
                if jump > max1:
                    max1 = jump
                    thr1 = q_vals[i - 1] + jump / 2
            # print(field_label,q_vals,max1)

            confident_jump = (
                config.threshold_params.MIN_JUMP
                + config.threshold_params.CONFIDENT_SURPLUS
            )
            # If not confident, then only take help of global_thr
            if max1 < confident_jump:
                if no_outliers:
                    # All Black or All White case
                    thr1 = global_thr
                else:
                    # TODO: Low confidence parameters here
                    pass

            # if(thr1 == 255):
            #     print("Warning: threshold is unexpectedly 255! (Outlier Delta issue?)",plot_title)

        # Make a common plot function to show local and global thresholds
        if plot_show and plot_title is not None:
            _, ax = plt.subplots()
            ax.bar(range(len(q_vals)), q_vals)
            thrline = ax.axhline(thr1, color="green", ls=("-."), linewidth=3)
            thrline.set_label("Local Threshold")
            thrline = ax.axhline(global_thr, color="red", ls=":", linewidth=5)
            thrline.set_label("Global Threshold")
            ax.set_title(plot_title)
            ax.set_ylabel("Bubble Mean Intensity")
            ax.set_xlabel("Bubble Number(sorted)")
            ax.legend()
            # TODO append QStrip to this plot-
            # appendSaveImg(6,getPlotImg())
            if plot_show:
                plt.show()
        return thr1

    def append_save_img(self, key, img):
        if self.save_image_level >= int(key):
            self.save_img_list[key].append(img.copy())

    def save_image_stacks(self, key, filename, save_dir):
        config = self.tuning_config
        if self.save_image_level >= int(key) and self.save_img_list[key] != []:
            name = os.path.splitext(filename)[0]
            result = np.hstack(
                tuple(
                    [
                        ImageUtils.resize_util_h(img, config.dimensions.display_height)
                        for img in self.save_img_list[key]
                    ]
                )
            )
            result = ImageUtils.resize_util(
                result,
                min(
                    len(self.save_img_list[key]) * config.dimensions.display_width // 3,
                    int(config.dimensions.display_width * 2.5),
                ),
            )
            ImageUtils.save_img(f"{save_dir}stack/{name}_{str(key)}_stack.jpg", result)

    def reset_all_save_img(self):
        for i in range(self.save_image_level):
            self.save_img_list[i + 1] = []
