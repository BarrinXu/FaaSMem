FROM faasmem_base
RUN pip3 install --no-cache-dir pyaes
RUN mkdir /proxy/data
COPY app.py  /proxy/
COPY data /proxy/data/
