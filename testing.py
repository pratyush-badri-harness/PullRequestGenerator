import requests
from bs4 import BeautifulSoup
from scipy.spatial.distance import cosine

cosSim = []
def scrape(prNum):
    try:
        URL = "https://github.com/harness/harness-core/pull/"
        prURL = URL+str(prNum)
        cmURL = prURL+"/commits"

        content = requests.get(url = cmURL).content
        soup = BeautifulSoup(content,'html.parser')

        scrapedCMs = soup.findAll('a','Link--primary text-bold js-navigation-open markdown-title')
        splitMessages = soup.findAll('pre','text-small ws-pre-wrap')


        commitMessages = []
        splitMessageCount = 0
        for i in range(1,len(scrapedCMs),2):
            tempStr = scrapedCMs[i].text[3:]
            if(tempStr.endswith('…')):
                tempStr = tempStr[:-3]
                tempStr = tempStr + (splitMessages[splitMessageCount].text[3:])
                splitMessageCount+=1
            commitMessages.append(tempStr)

        diffURL = prURL + ".diff"
        diff = requests.get(url=diffURL).content

        desc = requests.get(url = prURL).content
        soup = BeautifulSoup(desc,'html.parser')
        
        temp = soup.findAll('div','comment-body markdown-body js-comment-body soft-wrap css-overflow-wrap-anywhere user-select-contain d-block')
        realDesc = ""
        for iter in temp[0].findAll('p'):
            if(iter.text.startswith('https://harness') or iter.text.startswith('You can run multiple PR check triggers')):
                break
            realDesc += iter.text
        for iter in temp[0].findAll('li'):
            if(iter.text.startswith(' I\'ve')):
                break
            realDesc += iter.text
        print("Original Description:-\n")
        print(realDesc)
        print("----")

        embeddingURL = "http://35.202.125.234/embeddings"
        headers = {
            'accept' : 'application/json',
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJTVE8iLCJuYW1lIjoiSm9obiBEb2UiLCJpYXQiOjE1MTYyMzkwMjJ9.jfxeZZa8svIRisRy9NhcKeCWE6QXh3Cj0ksarw8kZlI',
            'Content-Type': 'application/json'
        }

        data = {
            "data": "%s"%realDesc,
            "model_name": "textembedding-gecko@001"
        }
        realEmbedding = requests.post(url=embeddingURL,headers = headers,json = data).json()["embeddings"]

        GenAIURL = "http://35.202.125.234/chat"
        headers = {
            'accept' : 'application/json',
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJTVE8iLCJuYW1lIjoiSm9obiBEb2UiLCJpYXQiOjE1MTYyMzkwMjJ9.jfxeZZa8svIRisRy9NhcKeCWE6QXh3Cj0ksarw8kZlI',
            'Content-Type': 'application/json'
        }

        if(len(diff)<20000):
            data = {
                "message": "Summarise these changes made while working in the current git branch to generate a pull request description based on the committed changes.  Do not state or list the files that were added, changed and deleted, instead explain how these changes affect the functionality of the product. Write the output in bullet points instead of a paragraph, with each point starting on a new line. The output of '\''git diff'\'' command is:%s and the list of commit messages are:%s"%(diff,commitMessages),
                "provider": "azureopenai",
                "context": " ",
                "examples": [
                    {
                    "input": " ",
                    "output": " "
                    }
                ],
                "model_name": "gpt3",
                "model_parameters": {
                    "temperature": 0,
                    "max_output_tokens": 1028,
                    "top_p": 0.95,
                    "top_k": 40
                }
            }
            prDescription = requests.post(url=GenAIURL,headers = headers,json = data).content
            prDescription = str(prDescription)
            endIndex = prDescription.find(",\"blocked\"")
            prDescription = prDescription[11:endIndex-2]
            prDescription = prDescription.replace("\\\\n-","\n -")
            print("Generated Description:-\n")
            print(prDescription)
            print("------------------")
            
            data = {
                "data": "%s"%prDescription,
                "model_name": "textembedding-gecko@001"
            }
            genEmbedding = requests.post(url=embeddingURL,headers = headers,json = data).json()["embeddings"]
            cosineSimilarity = 1-cosine(realEmbedding,genEmbedding)
            print("Cosine Similarity: %s"%cosineSimilarity)
            print("---------------------------------------------------------------------------------------------")
            cosSim.append(cosineSimilarity)

        else:
            combinedDescription = ""
            for i in range(0,(len(diff)//20000)+1,1):
                data = {
                    "message": "Summarise these changes made while working in the current git branch to generate a pull request description based on the committed changes.  Do not state or list the files that were added, changed and deleted, instead explain how these changes affect the functionality of the product. The output of '\''git diff'\'' command is:%s and the list of commit messages are:%s"%(diff[20000*i:min(20000*(i+1),len(diff))],commitMessages),
                    "provider": "azureopenai",
                    "context": " ",
                    "examples": [
                        {
                        "input": " ",
                        "output": " "
                        }
                    ],
                    "model_name": "gpt3",
                    "model_parameters": {
                        "temperature": 0,
                        "max_output_tokens": 1028,
                        "top_p": 0.95,
                        "top_k": 40
                    }
                }
                prDescription = requests.post(url=GenAIURL,headers = headers,json = data).content
                prDescription = str(prDescription)
                endIndex = prDescription.find(",\"blocked\"")
                prDescription = prDescription[11:endIndex-1]
                if(prDescription != "Server Erro"):
                    combinedDescription = combinedDescription + prDescription
            data = {
                "message": "Use this following paragraph to write a pull request description, explaining how these changes affect the functionality of the product. Write the output in bullet points instead of a paragraph, with each point starting on a new line.:%s"%combinedDescription,
                "context": " ",
                "examples": [
                    {
                    "input": " ",
                    "output": " "
                    }
                ],
                "model_name": "chat-bison",
                "model_parameters": {
                    "temperature": 0,
                    "max_output_tokens": 528,
                    "top_p": 0.95,
                    "top_k": 40
                }
            }
            prDescription = requests.post(url=GenAIURL,headers = headers,json = data).content
            prDescription = str(prDescription)
            endIndex = prDescription.find(",\"blocked\"")
            prDescription = prDescription[11:endIndex-2]
            prDescription = prDescription.replace("\\\\n-","\n -")
            prDescription = prDescription.replace("\\\\n*","\n *")

            data = {
                "data": "%s"%prDescription,
                "model_name": "textembedding-gecko@001"
            }
            genEmbedding = requests.post(url=embeddingURL,headers = headers,json = data).json()["embeddings"]
            cosineSimilarity = 1-cosine(realEmbedding,genEmbedding)
            cosSim.append(cosineSimilarity)
            print("Generated Description:-\n")
            print(prDescription)
            print("------------------")
            print("Cosine Similarity: %s"%cosineSimilarity)
            print("---------------------------------------------------------------------------------------------")
    except:
        return

prNums = [50823,50575,50524,50323,50208,50147,50043,49581,49252,49112,48735,48663,48501,47963,47957,47888,47507,47001,50531,50523,50339,50242,49826,49800,49723,49596,49559,49538,49297,49687,49425,49127,48895,48561,48290,48148,47737,46714,45792]
for prNum in prNums:
    scrape(prNum)
print(cosSim)
print(sum(cosSim)/len(cosSim))