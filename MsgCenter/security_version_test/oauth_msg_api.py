from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import configparser
import os
import json
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

# Constants for JWT
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"  # Should be in env var in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create FastAPI app
app = FastAPI(
    title="Message Center API",
    description="API for accessing configuration information for the AI SIEM system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Password hashing utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# User database - in production this should be a real database
# For this example, we'll use a simple dictionary
# Format: {"username": {"username": str, "hashed_password": str, "disabled": bool}}
users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("adminpassword"),
        "disabled": False,
    },
    "user": {
        "username": "user",
        "hashed_password": pwd_context.hash("userpassword"),
        "disabled": False,
    }
}

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class ConfigResponse(BaseModel):
    status: str
    data: Dict[str, Any]

# Config file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_EMBED_PATH = os.path.join(BASE_DIR, "config_embed.ini")
CONFIG_FACTORY_PATH = os.path.join(BASE_DIR, "config_factory.ini")

# Helper functions
def verify_password(plain_password, hashed_password):
    """Verify that the provided password matches the hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    """Get user from the database"""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(db, username: str, password: str):
    """Authenticate a user by username and password"""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current user from the JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Check if the current user is active"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def parse_config_file(file_path):
    """
    Parse a configuration file and return its contents as a dictionary
    
    Args:
        file_path (str): Path to the configuration file
    
    Returns:
        dict: Configuration as a dictionary
    """
    config = configparser.ConfigParser()
    config.read(file_path)
    
    result = {}
    for section in config.sections():
        result[section] = {}
        for key, value in config[section].items():
            result[section][key] = value
    
    return result

# Routes
@app.post("/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login, get an access token for future requests
    
    Args:
        form_data (OAuth2PasswordRequestForm): Form data with username and password
        
    Returns:
        Token: Access token for authentication
    """
    user = authenticate_user(users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/", tags=["Status"])
async def root():
    """
    Root endpoint that returns API status.
    
    Returns:
        dict: Status information
    """
    return {
        "status": "ok",
        "message": "Message Center API is running",
        "version": "1.0.0"
    }

@app.get("/config/embed", response_model=ConfigResponse, tags=["Configuration"])
async def get_embed_config(current_user: User = Depends(get_current_active_user)):
    """
    Get the embedding configuration
    
    Args:
        current_user (User): Current authenticated user
        
    Returns:
        ConfigResponse: Embedding configuration
    """
    try:
        config = parse_config_file(CONFIG_EMBED_PATH)
        return {
            "status": "success",
            "data": config
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load embed configuration: {str(e)}"
        )

@app.get("/config/embed/{section}", response_model=ConfigResponse, tags=["Configuration"])
async def get_embed_config_section(section: str, current_user: User = Depends(get_current_active_user)):
    """
    Get a specific section of the embedding configuration
    
    Args:
        section (str): The configuration section to retrieve
        current_user (User): Current authenticated user
        
    Returns:
        ConfigResponse: The requested configuration section
    """
    try:
        config = parse_config_file(CONFIG_EMBED_PATH)
        if section not in config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section '{section}' not found in embed config"
            )
        return {
            "status": "success",
            "data": {section: config[section]}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load embed configuration: {str(e)}"
        )

@app.get("/config/factory", response_model=ConfigResponse, tags=["Configuration"])
async def get_factory_config(current_user: User = Depends(get_current_active_user)):
    """
    Get the factory configuration
    
    Args:
        current_user (User): Current authenticated user
        
    Returns:
        ConfigResponse: Factory configuration
    """
    try:
        config = parse_config_file(CONFIG_FACTORY_PATH)
        return {
            "status": "success",
            "data": config
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load factory configuration: {str(e)}"
        )

@app.get("/config/factory/{section}", response_model=ConfigResponse, tags=["Configuration"])
async def get_factory_config_section(section: str, current_user: User = Depends(get_current_active_user)):
    """
    Get a specific section of the factory configuration
    
    Args:
        section (str): The configuration section to retrieve
        current_user (User): Current authenticated user
        
    Returns:
        ConfigResponse: The requested configuration section
    """
    try:
        config = parse_config_file(CONFIG_FACTORY_PATH)
        if section not in config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section '{section}' not found in factory config"
            )
        return {
            "status": "success",
            "data": {section: config[section]}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load factory configuration: {str(e)}"
        )

@app.get("/users/me/", response_model=User, tags=["Users"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get information about the currently authenticated user
    
    Args:
        current_user (User): Current authenticated user
        
    Returns:
        User: Current user information
    """
    return current_user

# Entry point for running the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)