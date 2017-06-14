from predict import hot_predict
from predict import initialize
import sys

def getOverlap(a, b):
	return max(0, min(a[1], b[1]) - max(a[0], b[0]))

weights_path = sys.argv[1]
hypes_path = sys.argv[2]
list_of_docs = sys.argv[3]

final_preds = []
tau = 0.25

init_params = initialize(weights_path, hypes_path)

doc_array = ['output/asm-cast-al-9-hd.png']
# def predict_boxes(path, init_params)
for path in doc_array:
	print(path)

	region_count = 0
	box_count = 0
	regions = {}
	# final_preds = []

	pred_anno = hot_predict(path, init_params, True)


	for box in pred_anno:
		box_count +=1
		# region_count +=1

		box_xs = [int(box['x1']), int(box['x2'])]
		box_ys = [int(box['y1']), int(box['y2'])]
		box_score = box['score']
		box_area = (box_xs[1] - box_xs[0]) * (box_ys[1] - box_ys[0])
		# print(box)


		if box_count == 1:
			print(region_count)
			regions[region_count] = [{'xs':box_xs, 'ys':box_ys, 'score':box_score}]
			# region_count += 1

		else:
			new_region = True
			for region, values in regions.iteritems():
				# print(regions)
				x_overlap = getOverlap(box_xs,values[0]['xs'])
				
				y_overlap = getOverlap(box_ys,values[0]['ys'])
				print('y overlap = {}'.format(y_overlap))
				
				overlap_area = x_overlap * y_overlap

				if overlap_area > (box_area*tau):
					print('overlap area = {}'.format(overlap_area))
					print('box area * tau = {}'.format(box_area*tau))
					regions[region_count].append({'xs':box_xs, 'ys':box_ys, 'score':box_score})
					new_region = False

			if new_region == True:
				region_count +=1
				regions[region_count] = [{'xs':box_xs, 'ys':box_ys, 'score':box_score}]
				# region_count += 1

	for region, values in regions.iteritems():
		print(len(regions))

		pred_count = 0
		max_score = 0
		best_pred = {}

		for idx, pred in enumerate(values):
			last_idx = len(values) - 1
			if pred_count == 0:
				best_pred = {'index':idx, 'score':pred['score']}
				pred_count +=1
			else:
				if pred['score'] > best_pred['score']:
					best_pred = {'index':idx, 'score':pred['score']}

				pred_count += 1


			print(idx)
			print(last_idx)
			if pred_count == last_idx:
				print('LAST INDEX')
				final_preds.append(values[best_pred['index']])

print(final_preds)









			



				# print(x_overlap)
				

	# print(pred_anno)

# image 


# parser = OptionParser(usage='usage: %prog [options] <image> <weights> <hypes>')
# parser.add_option('--gpu', action='store', type='int', default=0)
# parser.add_option('--tau', action='store', type='float', default=0.25)
# parser.add_option('--min_conf', action='store', type='float', default=0.2)