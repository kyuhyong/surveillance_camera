import cv2

camera = cv2.VideoCapture(0)  # Try 0, 1, or 2 if needed

if not camera.isOpened():
    print("❌ Failed to open the camera. Check connection or camera index.")
else:
    print("✅ Camera successfully opened.")

# Test capturing a single frame
success, frame = camera.read()

if success:
    cv2.imshow("Camera Test", frame)
    cv2.waitKey(3000)  # Display for 3 seconds
else:
    print("❌ Failed to capture frame from camera.")

camera.release()
cv2.destroyAllWindows()