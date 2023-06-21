import cv2
import face_recognition
import numpy as np
from azure.cosmosdb.table.tableservice import TableService
from azure.storage.blob import BlobServiceClient
import requests
import io

azure_connection_string = "DefaultEndpointsProtocol=https;AccountName=racha1125;AccountKey=j8KqI44FialfJRKG5zrgkovoroSKcXzd9lci5fQaAYiIsWzUZ659YBx+mR8/rEv/cHyCeZmjWS0j+AStbL0Rtg==;EndpointSuffix=core.windows.net"
container_name = "face-images"
table_name = "ProfileInfo"
attendance_table_name = "Attendance"

# Prompt the user for profile information
full_name = input("Enter your full name: ")
college_code = input("Enter your college code: ")

if college_code == "snist":
    # Connect to the storage account
    blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    # Check if the profile exists in the ProfileInfo table
    table_service = TableService(connection_string=azure_connection_string)
    profile_query = f"PartitionKey eq '{full_name}' and RowKey eq '{full_name}'"
    profiles = list(table_service.query_entities(table_name, filter=profile_query))
    profile_exists = len(profiles) > 0

    if profile_exists:
        # Retrieve the LinkedIn profile URL and profile photo URL from the existing profile
        profile = profiles[0]
        linkedin_profile_url = profile.linkedin_profile_url
        profile_picture_url = profile.profile_photo_url
        print("Profile already exists.")
    else:
        # Prompt the user for LinkedIn profile URL and profile photo URL
        linkedin_profile_url = input("Enter your LinkedIn profile URL: ")
        profile_picture_url = input("Enter the URL of your profile picture: ")

        # Retrieve the profile photo
        response = requests.get(profile_picture_url)
        profile_picture = response.content

        # Save the profile picture to Azure Blob Storage
        blob_name = f"{full_name}.jpg"
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(profile_picture)
        print("Profile picture saved successfully.")

        # Save the profile information to the ProfileInfo table
        profile_entity = {
            'PartitionKey': full_name,
            'RowKey': full_name,
            'linkedin_profile_url': linkedin_profile_url,
            'profile_photo_url': profile_picture_url
        }
        table_service.insert_or_replace_entity(table_name, profile_entity)

        print("Profile information saved successfully.")
    blob_client = container_client.get_blob_client(f"{full_name}.jpg")
    blob_data = blob_client.download_blob()
    # Load the face encodings from Azure Blob Storage
    known_face_encodings = []
    known_face_names = []
    image = face_recognition.load_image_file(blob_data)
    encoding = face_recognition.face_encodings(image)[0]
    known_face_encodings.append(encoding)
    known_face_names.append(f"{full_name}")  # Extract the name from blob name
    # Initialize variables for face recognition
    students = known_face_names.copy()
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True
    # Open the video capture
    video_capture = cv2.VideoCapture(0)
    while True:
        _, frame = video_capture.read()
        # Resize the frame to improve performance
        small_frame = cv2.resize(frame, (0, 0), fx=0.35, fy=0.35)
        rgb_small_frame = small_frame[:, :, ::-1]
        if process_this_frame:
            # Detect faces in the frame
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations, num_jitters=1)
            # face_encodings = face_recognition.face_encodings(frame, face_locations)
            face_names = []
            for face_encoding in face_encodings:
                # Compare the face encoding with known faces
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = ""
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
                face_names.append(name)
                # Check if the attendance entity already exists
                attendance_query = f"PartitionKey eq '{full_name}' and RowKey eq '{full_name}'"
                attendance_entities = list(table_service.query_entities(attendance_table_name, filter=attendance_query))
                attendance_exists = len(attendance_entities) > 0

                if not attendance_exists:
                    # Save the attendance to the Attendance table
                    attendance_entity = {
                        'PartitionKey': full_name,
                        'RowKey': full_name,
                        'attendance': 'Present'
                    }
                    table_service.insert_entity(attendance_table_name, attendance_entity)
                    print("Attendance saved successfully.")
                    # End the video capture
                    video_capture.release()
                    cv2.destroyAllWindows()
                    exit()
                else:
                    print("Attendance already saved")
                    # End the video capture
                    video_capture.release()
                    cv2.destroyAllWindows()
                    exit()

        # Display the resulting frame
        cv2.imshow('Video', frame)
        # Check for 'q' key press to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture handle and destroy windows
    video_capture.release()
    cv2.destroyAllWindows()
    # while True:
    #     _, frame = video_capture.read()
    #     # Resize the frame to improve performance
    #     small_frame = cv2.resize(frame, (0, 0), fx=0.35, fy=0.35)
    #     rgb_small_frame = small_frame[:, :, ::-1]
    #     if process_this_frame:
    #         # Detect faces in the frame
    #         face_locations = face_recognition.face_locations(rgb_small_frame)
    #         face_encodings = face_recognition.face_encodings(frame, face_locations, num_jitters=1)
    #         # face_encodings = face_recognition.face_encodings(frame, face_locations)
    #         face_names = []
    #         for face_encoding in face_encodings:
    #             # Compare the face encoding with known faces
    #             matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
    #             name = ""
    #             face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
    #             best_match_index = np.argmin(face_distances)
    #             if matches[best_match_index]:
    #                 name = known_face_names[best_match_index]
    #             face_names.append(name)
    #             # Check if the attendance entity already exists
    #             attendance_query = f"PartitionKey eq '{full_name}' and RowKey eq '{full_name}'"
    #             attendance_entities = list(table_service.query_entities(attendance_table_name, filter=attendance_query))
    #             attendance_exists = len(attendance_entities) > 0
    #
    #             if not attendance_exists:
    #                 # Save the attendance to the Attendance table
    #                 attendance_entity = {
    #                     'PartitionKey': full_name,
    #                     'RowKey': full_name,
    #                     'attendance': 'Present'
    #                 }
    #                 table_service.insert_entity(attendance_table_name, attendance_entity)
    #                 print("Attendance saved successfully.")
    #
    #             else:
    #                 print("Attendance already saved")
    #
    #     # # Display the results on the frame
    #     # for (top, right, bottom, left), name in zip(face_locations, face_names):
    #     #     top *= 4
    #     #     right *= 4
    #     #     bottom *= 4
    #     #     left *= 4
    #     #
    #     #     cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
    #     #     cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
    #     #     font = cv2.FONT_HERSHEY_DUPLEX
    #     #     cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
    #
    #     # Display the resulting frame
    #     cv2.imshow('Video', frame)
    #     # Check for 'q' key press to exit
    #     if cv2.waitKey(1) & 0xFF == ord('q'):
    #         break
    # # Release the video capture handle and destroy windows
    # video_capture.release()
    # cv2.destroyAllWindows()
else:
    print("Invalid college code. Face recognition is not available.")
