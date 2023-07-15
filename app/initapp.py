import nltk
#from fonetika.soundex import RussianSoundex
from nltk.corpus import stopwords

nltk.download('punkt')
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))
#soundex = RussianSoundex(delete_first_letter=True, code_vowels=True)

