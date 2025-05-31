from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import re
from django.contrib import messages
import pandas as pd
from .mongo_connect import client
from .face_detection_recognition_app import gen_frames, get_status_message, set_username, stop_frame_processing, load_encoding_data
from django.contrib.auth import authenticate
from io import BytesIO
from django.views.decorators.csrf import csrf_exempt
import tempfile
from .encode_faces import encode_and_store_images
import os

def proindex(request):
    return render (request,'before_login/proindex.html')

def sarbik_view(request):
    return render (request,'before_login/contact_us/sarbik.html')

def tania_view(request):
    return render (request,'before_login/contact_us/tania.html')

def sarbani_view(request):
    return render (request,'before_login/contact_us/sarbani.html')

def manish_view(request):
    return render (request,'before_login/contact_us/manish.html')

def deblina_view(request):
    return render (request,'before_login/contact_us/deblina.html')

def contact(request):
    return render(request, 'before_login/contact.html')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def stylesheet(request):
    total_count = 0
    recognized_count = 0
    day_wise_data = {'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0, 'Friday': 0, 'Saturday': 0}

    try:
        db = client[request.user.username]
        summary_collection = db["daily_attendance_summary"]

        # Get all documents and build day-wise recognized counts
        for doc in summary_collection.find():
            day = doc.get('day')
            count = doc.get('recognized_count', 0)
            if day in day_wise_data:
                day_wise_data[day] += count  # Sum up if multiple entries for a day

        recognized_count = summary_collection.find_one(sort=[('_id', -1)]).get('recognized_count', 0)

        if "Datasheet" in db.list_collection_names():
            total_count = db["Datasheet"].count_documents({})
            if total_count == 0:
                total_count = False
    except Exception as e:
        print(f"Error in stylesheet view: {e}")

    return render(request, 'after_login/stylesheet.html', {
        'row_count': total_count,
        'recognized_count': recognized_count,
        'day_wise_data': list(day_wise_data.values()),  # just values like [15, 10, 0, ...]
        'day_names': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']  # fixed labels for frontend
    })

@login_required
def home(request):
    return render(request, 'after_login/home.html')

def login_signup(request):
    signup_form = UserCreationForm()
    login_form = AuthenticationForm()
    active_form = 'login'  # default view

    if request.method == 'POST':
        if 'signup' in request.POST:
            active_form = 'signup'
            username = request.POST.get('username')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')

            password_errors = []

            # Check if username already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, "Oops! Looks like that username's already in use. Try a fresh one that's uniquely you!", extra_tags='signup')
            else:
                # Custom password validation
                if password1 != password2:
                    password_errors.append("Oops! Those passwords didn't match — try typing them again.")
                elif len(password1) < 8:
                    password_errors.append("Password too short! Let's go with at least 8 characters for a secure experience.")
                elif username.lower() in password1.lower():
                    password_errors.append("Your password shouldn't be a twin of your username — let's keep things unpredictable!")
                elif not (re.search(r'[A-Za-z]', password1) and re.search(r'\d', password1) and re.search(r'[^A-Za-z0-9]', password1)):
                    password_errors.append("Mix it up! Add letters, numbers, and symbols to make your password rock-solid.")

                if password_errors:
                    for err in password_errors:
                        messages.error(request, err, extra_tags='signup')
                else:
                    signup_form = UserCreationForm(request.POST)
                    if signup_form.is_valid():
                        user = signup_form.save()
                        db = client[user.username]
                        db.login_info.insert_one({'username': user.username})
                        login(request, user)
                        return redirect('stylesheet')
                    else:
                        messages.error(request, "Signup failed. Please fix the highlighted fields.", extra_tags='signup')

        elif 'login' in request.POST:
            username = request.POST.get('username')
            user = User.objects.filter(username=username).first()

            if not user:
                messages.error(request, "We couldn't find that username.<br>Double-check it or go ahead and create a new account!", extra_tags='login')
            else:
                login_form = AuthenticationForm(request, data=request.POST)
                if login_form.is_valid():
                    user = login_form.get_user()
                    login(request, user)
                    return redirect('stylesheet')
                else:
                    messages.error(request, "🔐 Incorrect password — please try again.", extra_tags='login')


    return render(request, 'before_login/login_signup.html', {
        'signup_form': signup_form,
        'login_form': login_form,
        'active_form': active_form
    })

@login_required
def logout_view(request):
    logout(request)
    return redirect('proindex')


@login_required
@csrf_exempt
def upload_excel(request):
    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            return render(request, 'after_login/upload_excel.html', {'message': 'No file uploaded'})

        excel_file = request.FILES['excel_file']

        try:
            # Load the Excel file
            df = pd.read_excel(excel_file, engine='openpyxl')

            # Count the number of rows
            row_count = len(df)
            request.session['row_count'] = row_count  # Save to session

            db = client[request.user.username]
            datasheet_collection = db["Datasheet"]
            attendance_collection = db["Attendance"]
            #recognized_today_collection = db["recognized_today"]

            if 'Attendance' in df.columns:
                attendance_data = df[['ID', 'Attendance']].to_dict(orient='records')
                attendance_collection.delete_many({})
                attendance_collection.insert_many(attendance_data)

                df['Attendance'] = [[] for _ in range(len(df))]
            else:
                df['Attendance'] = [[] for _ in range(len(df))]

            datasheet_collection.delete_many({})
            datasheet_collection.insert_many(df.to_dict(orient='records'))

            #recognized_today_collection.delete_many({})

            return redirect('stylesheet')  # Use named URL instead of render

        except Exception as e:
            return render(request, 'after_login/upload_excel.html', {'message': f'Error reading Excel file: {str(e)}'})

    return render(request, 'after_login/upload_excel.html')


@login_required
@csrf_exempt
def upload_zip(request):
    if request.method == 'POST' and request.FILES.get('zip_file'):
        zip_file = request.FILES['zip_file']
        username = request.user.username

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
            for chunk in zip_file.chunks():
                temp_zip.write(chunk)
            temp_zip_path = temp_zip.name

        try:
            encode_and_store_images(temp_zip_path, username)
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
        finally:
            os.remove(temp_zip_path)

        return render(request, 'after_login/stylesheet.html', {'message': 'Images Uploaded'})

    return render(request, 'after_login/upload_zip.html')

@login_required
def delete_data(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(username=request.user.username, password=password)

        if user:
            db = client[request.user.username]
            collections_to_check = ["Datasheet", "Attendance", "Image_info"]

            collections_exist_with_data = False

            for collection_name in collections_to_check:
                if collection_name in db.list_collection_names():
                    count = db[collection_name].count_documents({})
                    if count > 0:
                        collections_exist_with_data = True
                        break  # At least one collection has data

            if collections_exist_with_data:
                # Proceed with deletion
                for collection_name in collections_to_check:
                    if collection_name in db.list_collection_names():
                        db[collection_name].delete_many({})
                messages.success(request, "All your data has been deleted.")
            else:
                messages.info(request, "No files are present to delete.")
        else:
            messages.error(request, "Wrong password. Please try again.")

    return render(request, 'after_login/delete_data.html')

@login_required
def delete_account(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(username=request.user.username, password=password)

        if user:
            username = request.user.username
            if username in client.list_database_names():
                client.drop_database(username)

            User.objects.filter(username=username).delete()
            logout(request)
            return redirect('proindex')
        else:
            messages.error(request, "Wrong password. Please try again.")

    return render(request, 'after_login/delete_account.html')

@login_required
def start_attendance(request):
    username = request.user.username
    set_username(username)

    if not load_encoding_data():
        return HttpResponse("Failed to load encoding data.", status=500)

@login_required
def download_attendance(request):
    db = client[request.user.username]
    datasheet_collection = db["Datasheet"]
    attendance_collection = db["Attendance"]

    attendance_data = {}
    for entry in attendance_collection.find({}, {'_id': 0}):
        _id = entry.get('ID')
        attendance_count = entry.get('Attendance', 0)  # Integer attendance count
        attendance_data[_id] = attendance_count

    # Step 2: Read employee data from Datasheet and add attendance counts
    result = []
    for entry in datasheet_collection.find({}, {'_id': 0}):
        _id = entry.get('ID')
        name = entry.get('Name')
        attendance_list = entry.get('Attendance', [])
        attendance_length = len(attendance_list)  # Current list length

        # Add the attendance count from the Attendance collection if available
        additional_attendance = attendance_data.get(_id, 0)
        total_attendance = attendance_length + additional_attendance

        result.append({
            'ID': _id,
            'Name': name,
            'Attendance Count': total_attendance
        })

    # Step 3: Export the data to an Excel file
    df = pd.DataFrame(result)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance Report')

    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=Attendance_Report.xlsx'
    return response

@login_required
def attendance_view(request):
    db = client[request.user.username]

    # Check if 'Datasheet' collection exists
    if 'Datasheet' not in db.list_collection_names():
        messages.error(request, "Please upload your employee details first.")
        return redirect('upload_excel')

    datasheet_collection = db["Datasheet"]

    if datasheet_collection.count_documents({}) == 0:
        messages.error(request, "Please upload your employee details first.")
        return redirect('upload_excel')
    
    if 'Image_info' not in db.list_collection_names():
        messages.error(request, "Please upload your employee's images first.")
        return redirect('upload_zip')
    
    image_collection = db["Image_info"]

    if image_collection.count_documents({}) == 0:
        messages.error(request, "Please upload your employee's images first.")
        return redirect('upload_zip')
    
    return render(request, 'after_login/attendance.html')


@login_required
def video_feed(request):
    set_username(request.user.username)
    return StreamingHttpResponse(gen_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

@login_required
def get_message(request):
    message = get_status_message()

    if not message:
        message = 'No face recognized yet.'

    return JsonResponse({'message': message})

@login_required
def stop_video_feed(request):
    stop_frame_processing()
    return JsonResponse({'message': 'Video feed stopped'})

@login_required
def mark_message_seen(request):
    request.session['latest_message'] = ""
    return JsonResponse({'status': 'cleared'})
