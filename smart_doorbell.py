# camera setup taken from https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/
# motion detection adapted from https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/

# import the necessary packages
from picamera.array import PiRGBArray
from picamera import PiCamera
import imutils
import time
from datetime import datetime
import cv2
import threading
from sense_hat import SenseHat

# prime alarm thread
sense = SenseHat()
red = (255, 0, 0)
white = (255, 255, 255)
thread = None

def displayMessage():
	sense.show_message("ALARRRRRRRM!", text_colour=red, back_colour=white, scroll_speed=0.1)
	sense.clear()
	#print('Alarm has ended.')

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 32
rawCapture = PiRGBArray(camera, size=(640, 480))

# allow the camera to warmup
print('Starting camera. Move out of its sight for initialization.')
time.sleep(0.5)

# initialize helper variables
counter = 0
firstFrame = None
recording = False


# continuosly capture frames from the camera
for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
	# grab the raw NumPy array representing the image
	image = frame.array

	# clear the stream in preparation for the next frame
	rawCapture.truncate(0)
	
	# resize the frame, convert it to grayscale, and blur it
	height, width = image.shape[:2]
	image = cv2.resize(image, (width / 4, height / 4), interpolation = cv2.INTER_CUBIC)
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	blurred = cv2.GaussianBlur(gray, (21, 21), 0)

	# get current date and time
	date = datetime.now().strftime("%d_%m_%y-%H_%M_%S") 

	# throw away the first couple frames because they seem to be instable frequently
	if counter < 5 or firstFrame is None:
		counter += 1
		firstFrame = blurred
		continue
	elif counter == 5:
		print(date + ' | Initialization complete. Smart Doorbell enabled.')
		counter += 1

	# compute the absolute difference between the current frame and first frame
	frameDelta = cv2.absdiff(firstFrame, blurred)
	thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]
	
	# dilate the thresholded image to fill in holes, then find contours on thresholded image
	thresh = cv2.dilate(thresh, None, iterations=2)
	cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cnts = imutils.grab_contours(cnts)

	# motion detected
	if len(cnts) > 0:
	
		# start recording
		if recording == False:
			print(date + ' | Movement detected: Starting to record video.')
			camera.start_recording(date+'.h264')
			recording = True

		# search for faces
		cascPath = "haarcascade_frontalface_default.xml"
		faceCascade = cv2.CascadeClassifier(cascPath)
		faces = faceCascade.detectMultiScale(
			gray,
			scaleFactor=1.1,
			minNeighbors=5,
			minSize=(30, 30),
			# when the values are smaller, the face to detect can be smaller
			flags=cv2.cv.CV_HAAR_SCALE_IMAGE
		)

		# face detected
		if(len(faces) > 0):
			for (x,y,w,h) in faces:
				cv2.rectangle(image,(x,y),(x+w,y+h),(116, 244, 66),2)

			# sounding alarm in seperate thread
			if thread == None or not thread.isAlive():
				print(date + ' | Face detected: Sounding alarm.')
				thread = threading.Thread(target=displayMessage)
				thread.start()

	# no more motion detected
	elif recording == True:
		camera.stop_recording()
		recording = False
		print(date + ' | Movement has ended: Stopping recording.')

	# control center, comment to reduce strain
	cv2.imshow("Motion Feed", thresh)
	cv2.imshow("Face Feed", image)
	key = cv2.waitKey(1) & 0xFF
	if key == ord('q'):
		print(date + ' | Smart doorbell disabled. Ending program.')
		raise SystemExit