FROM faasmem_base
RUN pip3 install --no-cache-dir torch  --extra-index-url https://download.pytorch.org/whl/cpu
RUN pip3 install --no-cache-dir transformers
COPY app.py  /proxy/
RUN mkdir /proxy/model
COPY model /proxy/model/
