from django.shortcuts import render, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer
from datetime import datetime, timezone, timedelta
import jwt
from jwt import ExpiredSignatureError, InvalidSignatureError
import secrets
from django.conf import settings
from pymongo import MongoClient
from django.contrib.auth.hashers import make_password, check_password

# MongoDB Connection
client = MongoClient('mongodb://localhost:27017/')
db = client['recipe_db']
user_collection = db['users']

# register user template
# def register_template(request):
#     return render(request, 'register.html')

def home(request):
    return render(request, 'home.html')
def dashboard(request):
    return render(request,'dashboard.html')


# resgister new user
@api_view(['POST'])

def register_user_api(request):
    serializer = UserSerializer(data=request.data)

    if serializer.is_valid():
        data = serializer.validated_data
        password_hash = make_password(data['password'])

        user = {
            "username": data["username"],
            "password_hash": password_hash,
            "email": data["email"],
            "is_active": data["is_active"],
            "created_at": datetime.now(timezone.utc)
        }
        
        if user_collection.find_one({"username": user["username"]}):
            return Response({
                        "sucess": False,
                        "message": "Username already exists"
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        db.users.insert_one(user)
        return Response({
            "success": True,
            "message": "User created successfully",
            }, status=status.HTTP_201_CREATED)
    
    
    return Response({
        "succes": False,
        "message": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# user login
@api_view(['POST'])
def login_user_api(request):
    email = request.data.get("email")
    password = request.data.get("password")

    user = db.users.find_one({'email':email})
    print(user['_id'])
    if user and check_password(password, user["password_hash"]):
        print(user,check_password(password, user["password_hash"]) )
        existing_tokens = db.tokens.find_one({'user_id': user['_id']})
        print(existing_tokens)
       
        if not existing_tokens:
            access_token_exp = int((datetime.now(timezone.utc)+timedelta(days=1)).timestamp())
            access_token_iat = int(datetime.now(timezone.utc).timestamp())
            refresh_token_exp = int((datetime.now(timezone.utc)+timedelta(days=13)).timestamp())

            payload = {
                "username":user["username"],
                "user_id":str(user["_id"]),
                "email":user["email"],
                "exp": access_token_exp,
                "refresh_exp": refresh_token_exp,
                "iat": access_token_iat
            }
            
            access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            refresh_token = secrets.token_urlsafe(64)

            db.tokens.update_one(
                {"user_id": user['_id']},
                {"$set": {
                    "access": access_token,
                    "refresh": refresh_token,
                    "updated_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )

        try:
            jwt.decode(existing_tokens["access"], settings.SECRET_KEY, algorithms=['HS256'])
            # print(jwt.decode(existing_tokens["access"], settings.SECRET_KEY, algorithms=['HS256']))

            access_token = existing_tokens["access"]
            refresh_token = existing_tokens["refresh"]
            
        except jwt.ExpiredSignatureError:
            return Response({
                "success": False,
                "message":"Access token has expired!",
                "refresh_token": existing_tokens["refresh"]
            }, status=status.HTTP_401_UNAUTHORIZED)
           
        except jwt.InvalidSignatureError:
            return Response({
                "success": False,
                "message":"Invalid access token",
                "refresh_token": existing_tokens["refresh"]
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
                "success": True,
                "message": "Logged in successfully",
                "data": {
                    "access": access_token,
                    "refresh": refresh_token
                }
        }
        )
    
    return Response({
            "success": False,
            "message": "Invalid credentials"
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def renew_access_token(request):
    refresh_token = request.data.get("refresh_token")

    if not refresh_token:
        return Response({
            "success": False,
            "message": "Refresh token is required"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    token_entry = db.tokens.find_one({"refresh": refresh_token})

    if not token_entry:
        return Response({
            "success": False,
            "message": "Invalid refresh token"
        }, status=status.HTTP_404_NOT_FOUND)
    
    current_time = datetime.now(timezone.utc)
    if token_entry["refresh_exp"] < int(current_time.timestamp()):
        return Response({
            "success": False,
            "message": "Refresh token has expired"
        }, status=status.HTTP_401_UNAUTHORIZED)

    user_id = token_entry["user_id"]
    user = db.users.find_one({"_id": user_id})

    if not user:
        return Response({
            "success": False,
            "message":"User not found"
        }, status= status.HTTP_401_UNAUTHORIZED)
    
    access_token_exp = int((current_time+timedelta(days=1)).timestamp())
    access_token_iat = int(current_time.timestamp())

    payload = {
                "username":user["username"],
                "user_id":str(user["_id"]),
                "email":user["email"],
                "exp": access_token_exp,
                "iat": access_token_iat,
                "refresh_exp": token_entry["refresh_exp"]
            }
    
    new_access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    db.tokens.update_one(
        {"user_id": user_id},
        {
            "$set":{
                "access":new_access_token,
                "exp": access_token_exp,
                "iat": access_token_iat,
                "updated_at": current_time
            }
        },
        upsert=True
    )

    return Response({
        "success": True,
        "message": "Successfully refreshed access token",
        "data":{
            "new_token": new_access_token
        }
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def profile_view(request):
    user = request.user

    return Response({
        "success": True,
        "message": "Authenticated user",
        "data":{
            "username": user.username,
            "email": user.email
        }
    }, status=status.HTTP_200_OK)