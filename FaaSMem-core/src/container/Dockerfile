FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1
#COPY pip.conf /etc/pip.conf
#RUN sed -i "s@http://deb.debian.org@http://mirrors.ustc.edu.cn@g" /etc/apt/sources.list
#RUN sed -i "s@http://security.debian.org@http://mirrors.ustc.edu.cn@g" /etc/apt/sources.list
RUN mkdir /proxy
COPY proxy.py /proxy/
WORKDIR /proxy
EXPOSE 5000

RUN apt clean
RUN apt update
RUN pip3 install --no-cache-dir gevent flask requests

CMD ["python3", "/proxy/proxy.py"]