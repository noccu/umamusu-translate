This model is trained by MingShiba as part of Sugoi Translator/VN OCR.

How to use it:
Install fairseq >=10.0.2
Currently there is an issue with the pip version on windows, so you need to clone the git repo and install it yourself:

git clone https://github.com/pytorch/fairseq
cd fairseq
pip install --editable ./


Then install sentencepiece:

py -m pip install sentencepiece

Download the model files from the most recent model or https://drive.google.com/file/d/1KgAsQzI-A0D8vmNIekwIRKlflGw9xz3i/view
Extract the archive in the sugoi-model folder
You should end up with src/data/sugoi-model/japaneseModel etc.

Then run the usual machinetl.py with the extra arg: -model sugoi