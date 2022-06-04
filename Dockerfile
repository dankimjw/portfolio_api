FROM python:3.9
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE ${PORT}
CMD [ "python", "main.py" ]
