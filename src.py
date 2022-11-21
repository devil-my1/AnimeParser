import requests
from bs4 import BeautifulSoup as bs
import asyncio
import json
import csv
import time
from functools import partial
from datetime import datetime
from source.models.anime_model import Anime, Season

ulrs = ["https://zoro.to/top-airing",
        "https://zoro.to/most-popular"]
headers = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36x-requested-with: XMLHttpRequest",
    "accept": "*/*"
}


def loading_bar(iter, total, suffix="", prefix="", dec=1, leng=100, fill_char=">"):
    percent = ("{0:." + str(dec)+"f}").format(100*(iter/total))
    fill_leng = leng * iter // total
    bar = fill_char * fill_leng + "-" * (leng-fill_leng)
    print(f"\r{prefix}  |{bar}| {percent}% {suffix}", end="\r")


def save_on_json(data: list[Anime]):
    with open("./AnimeParser/data/result.json", "w", encoding="utf-8") as fs:
        json.dump(data, fs, indent=4,
                  default=anime_to_dict_encoder, ensure_ascii=False)


def save_on_csv(data: list[Anime]):
    with open("./AnimeParser/data/result.csv", "w") as fs:
        writer = csv.writer(fs, delimiter=";")
        writer.writerow(
            ("Title", "Jp_Title", "Aired", "Genres", "IsForAdult",
             "Discription", "Rate", "Status", "Link", "Seasons")
        )

    with open("./AnimeParser/data/result.csv", "a", encoding="utf-8") as fs:
        writer = csv.writer(fs, delimiter=";")

        for anime in data:
            seasons_str = ""
            if anime.seasons:
                for x in list(map(vars, anime.seasons)):
                    seasons_str += f"Name: {x['name']}\nLink: {x['url_link']}\n\n"

            writer.writerow(
                (
                    anime.name,
                    anime.jp_name,
                    anime.aired.strftime("%Y年%m月%d日") if not isinstance(
                        anime.aired, str) else anime.aired,
                    ", ".join(anime.genres),
                    anime.is_for_adult,
                    anime.discription.replace("\r\n\r", "") if len(
                        anime.discription) < 300 else anime.discription.replace("\r\n\r", "")[0:300]+"...",
                    anime.mal_score,
                    anime.status,
                    anime.url_link,
                    seasons_str
                )
            )


def anime_to_dict_encoder(anime: Anime) -> dict:
    dict = {
        "Title": anime.name,
        "Jp_Title": anime.jp_name,
        "Aired": anime.aired.strftime("%Y年%m月%d日") if not isinstance(anime.aired, str) else anime.aired,
        "Genres": anime.genres,
        "IsForAdult": anime.is_for_adult,
        "Discription": anime.discription.replace("\r\n\r", "") if len(anime.discription) < 300 else anime.discription.replace("\r\n\r", "")[0:300]+"...",
        "Rate": anime.mal_score,
        "Status": anime.status,
        "Link": anime.url_link,
        "Seasons": list(map(vars, anime.seasons)) if anime.seasons is not None else None,
    }

    return dict


def save_data_info(url: str, selected: str, saving_method: int = 1) -> list[Anime]:
    responce = requests.get(url, headers=headers)
    soup = bs(responce.content, "html.parser")
    pages = int(soup.find(class_="pagination").findAll("a",
                                                       class_="page-link")[-1].get("href").replace(f"/{selected}?page=", ""))
    anime_cards = soup.find_all(class_="film-poster-ahref item-qtip")
    animes = []
    count = 0

    for page in range(2, pages+1):
        if count == 0:
            for x in anime_cards:
                animes.append(get_anime_data(x.get('href')))
                count += 1
                loading_bar(count, len(anime_cards),
                            prefix=f" Start to get data from page {page-1}:", leng=len(anime_cards))
            print(f"\nPage {page-1} done!")

        req = requests.get(url, headers=headers, params={"page": page})
        soup = bs(req.content, "html.parser")
        anime_cards = soup.find_all(class_="film-poster-ahref item-qtip")

    if saving_method == 1:
        save_on_json(animes)
    else:
        save_on_csv(animes)
    print("All data is has been saved.")
    return animes


def get_anime_data(anime_id) -> Anime:
    url = "https://zoro.to" + anime_id
    res = requests.get(url, headers=headers)
    soap = bs(res.text, "html.parser")
    anime_info = Anime()
    info = soap.find(class_="anisc-info").find_all("span", class_="name")

    anime_info.name = soap.find(
        class_="film-name dynamic-name").get("data-jname")
    anime_info.jp_name = info[0].text

    anime_info.discription = soap.find(class_="film-description").text.strip()

    try:
        anime_info.genres = [x.text for x in soap.find(
            "div", class_="item-list").find_all("a")]
    except AttributeError:
        anime_info.genres = []
    date = info[2 if len(info) == 7 else 1].text.split("to")[
        0].replace(",", "").strip()
    anime_info.aired = datetime.strptime(date, '%b %d %Y').date()
    anime_info.mal_score = info[-1].text if info[-1].text != "?" else "unknown yet"
    anime_info.is_for_adult = soap.find(
        class_="anisc-poster").find(class_="tick tick-rate") is not None
    anime_info.status = info[-2].text
    anime_info.url_link = url

    seasons = soap.find(class_="os-list")
    if seasons:
        anime_info.seasons = []
        for s in seasons.find_all("a"):
            anime_info.seasons.append(
                Season(s.get("title"), "https://zoro.to"+s.get("href")))

    return anime_info


async def get_saver_async(url: str, pages: int):
    loop = asyncio.get_event_loop()
    req_data = {
        "url": url,
        "headers": headers
    }

    animes = []
    tasks = []

    def cb(a):
        animes.append(a)

    for page in range(1, pages+1):
        req_data["params"] = {"page": page}
        responce = await loop.run_in_executor(None, partial(requests.get, **req_data))
        soup = bs(responce.content, "html.parser")
        anime_cards = soup.find_all(class_="film-poster-ahref item-qtip")

        loading_bar(page, pages,
                    prefix=f" Start to get data from page {page}:", leng=pages, suffix="done")

        for x in anime_cards:
            tasks.append(asyncio.create_task(
                get_anime_data_async(x.get('href'), cb)))

        await asyncio.gather(*tasks)

    print()
    return animes


async def get_anime_data_async(anime_id: str, cb):
    loop = asyncio.get_event_loop()
    url = "https://zoro.to" + anime_id
    req_data = {
        "url": url,
        "headers": headers
    }

    responce = await loop.run_in_executor(None, partial(requests.get, **req_data))
    soap = bs(responce.text, "html.parser")
    anime_info = Anime()

    info = soap.find(class_="anisc-info").find_all("span", class_="name")

    anime_info.name = soap.find(
        class_="film-name dynamic-name").get("data-jname")
    anime_info.jp_name = info[0].text

    anime_info.discription = soap.find(class_="film-description").text.strip()

    try:
        anime_info.genres = [x.text for x in soap.find(
            "div", class_="item-list").find_all("a")]
    except AttributeError:
        anime_info.genres = []

    date = info[2 if len(info) == 7 else 1].text.split("to")[
        0].replace(",", "").strip()
    try:
        anime_info.aired = datetime.strptime(date, '%b %d %Y').date()
    except:
        anime_info.aired = date
    anime_info.mal_score = info[-1].text if info[-1].text != "?" else "unknown yet"
    anime_info.is_for_adult = soap.find(
        class_="anisc-poster").find(class_="tick tick-rate") is not None
    anime_info.status = info[-2].text
    anime_info.url_link = url

    seasons = soap.find(class_="os-list")
    if seasons:
        anime_info.seasons = []
        for s in seasons.find_all("a"):
            anime_info.seasons.append(
                Season(s.get("title"), "https://zoro.to"+s.get("href")))

    cb(anime_info)

# 24.393


def run_async():
    try:

        check = int(input(
            "Which data do u want to get:\n1:Top Airing\n2:Most Popular\n--> "))
        saving_method = int(
            input("Select saving data method:\n1:Json file?\n2:CSV file?\n-->"))
        if check <= 2 and saving_method <= 2:
            url = ulrs[check-1]
            responce = requests.get(url, headers=headers)
            soup = bs(responce.content, "html.parser")
            file_name = url.replace("https://zoro.to/", "")
            pages = int(soup.find(class_="pagination").findAll("a",
                                                               class_="page-link")[-1].get("href").replace(f"/{file_name}?page=", ""))

            animes_res = asyncio.run(
                get_saver_async(url, pages))

            if saving_method == 1:
                save_on_json(animes_res)
            else:
                save_on_csv(animes_res)

            return 1
        else:
            raise ValueError()
    except ValueError as er:
        print(f"Incorrect input, try again!\nErorr: {er}")


def main():

    try:
        check = int(input(
            "Which data do u want to get:\n1:Top Airing\n2:Most Popular\n--> "))
        saving_method = int(
            input("Select saving data method:\n1:Json file?\n2:CSV file?\n-->"))
        if check <= 2 and saving_method <= 2:
            url = ulrs[check-1]
            file_name = url.replace("https://zoro.to/", "")
            print("Getting the %s..." %
                  file_name.replace("-", " ").capitalize())
            save_data_info(ulrs[check-1], url.split("/")[-1], saving_method)
            return 1
        else:
            raise ValueError()
    except ValueError as er:
        print(f"Incorrect input, try again!\nErorr: {er}")


if __name__ == "__main__":
    start = time.time()
    run_async()
    end = time.time() - start
    print(f"The function process has been done in: {end:.3f}")
