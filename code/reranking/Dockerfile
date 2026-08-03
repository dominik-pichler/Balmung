FROM --platform=linux/amd64 python:3.6.15-slim-bullseye

RUN apt-get update && apt-get install -y make build-essential
RUN pip install jsonnet --no-build-isolation  
RUN pip install --upgrade pip
RUN pip install allennlp==1.2.2

RUN pip install blingfire==0.1.7
RUN pip install PyYAML==5.4
RUN pip install transformers==3.5.1
RUN pip install --find-links https://download.pytorch.org/whl/torch_stable.html torch==1.6.0

RUN pip install overrides

# convenience
RUN apt-get install -y git
RUN pip install numpy pandas matplotlib seaborn

# jupyter server
# attaching vscode can be buggy: https://github.com/microsoft/vscode-remote-release/issues/8169#issuecomment-1543987445
RUN pip install jupyter jupyterlab jupyter_contrib_nbextensions
ENV JUPYTER_ENABLE_LAB=yes
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--allow-root", "--no-browser", "--ServerApp.token=''", "--ServerApp.password=''", "--ServerApp.allow_origin='*'", "--ServerApp.disable_check_xsrf=True", "--ServerApp.allow_root=True", "--ServerApp.open_browser=False", "--ServerApp.disable_check_xsrf=True", "--ServerApp.disable_check_xsrf=True"]
EXPOSE 8888