from webbrowser import get
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson.objectid import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)

app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão com MongoDB
client = MongoClient("mongodb://localhost:27018/")
db = client["aula_fastapi"]
users_collection = db["users"]


class User(BaseModel):
    name: str
    email: str
    senha: str
    idade: int


class UserLogin(BaseModel):
    email: str
    senha: str


class Token(BaseModel):
    access_token: str
    token_type: str


# Segurança
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "sua-chave-ultra-secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id or not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Token inválido")

        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
            )

        user["_id"] = str(user["_id"])
        del user["senha"]
        return user

    except JWTError:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Token inválido ou expirado"
        )


# GET /users - List todos os usuários
@app.get("/users", status_code=HTTP_200_OK)
def get_all_users():
    try:
        users = []
        for user in users_collection.find():
            user["_id"] = str(user["_id"])  # Converte ObjectId para string
            users.append(user)
        return users
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao acessar o banco de dados",
        )


# DELETE /users - Deleta todos os usuários com confirmação
@app.delete("/users")
def delete_all_users(confirm: bool = False):
    if not confirm:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Acesso negado: confirmação obrigatória",
        )

    result = users_collection.delete_many({})
    return JSONResponse(
        status_code=HTTP_200_OK,
        content={"message": f"{result.deleted_count} usuários deletados"},
    )


@app.post("/users", status_code=HTTP_201_CREATED)
def create_user(user: User):
    try:
        if users_collection.find_one({"email": user.email}):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail="Email já cadastrado"
            )

        user_dict = user.dict()
        user_dict["senha"] = hash_password(user_dict["senha"])
        result = users_collection.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        del user_dict["senha"]

        return JSONResponse(
            status_code=HTTP_201_CREATED,
            content={"message": "Usuário criado com sucesso", "user": user_dict},
        )
    except Exception:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao criar usuário"
        )


@app.get("/me", status_code=HTTP_200_OK)
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/login", response_model=Token)
def login(user: UserLogin):
    user_db = users_collection.find_one({"email": user.email})
    if not user_db or not verify_password(user.senha, user_db["senha"]):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Credenciais inválidas"
        )

    token = create_access_token(data={"sub": str(user_db["_id"])})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/users/{user_id}", status_code=HTTP_200_OK)
def get_user_by_id(user_id: str):
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="ID inválido")

        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
            )

        user["_id"] = str(user["_id"])
        return user
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao buscar usuário"
        )


@app.delete("/users/{user_id}", status_code=HTTP_200_OK)
def delete_user_by_id(user_id: str):
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="ID inválido")

        result = users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
            )

        return {"message": "Usuário deletado com sucesso"}
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao deletar usuário"
        )


@app.put("/users/{user_id}", status_code=HTTP_200_OK)
def update_user(user_id: str, user: User):
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="ID inválido")

        update_data = user.dict()
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
            )

        return {"message": "Usuário atualizado com sucesso"}
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar usuário",
        )
