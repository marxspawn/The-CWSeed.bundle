CW_SEED = 'http://www.cwseed.com'
CW_SEED_SHOWS = 'http://www.cwseed.com/shows'
CW_ROOT = 'http://www.cwtv.com'
PREFIX = '/video/thecwseed'
NAME = 'CW SEED'

ICON = 'icon-default.jpg'
RE_JSON = Regex('CWSEED.Site.video_data.videos = (.+);\n')

####################################################################################################
def Start():

    ObjectContainer.title1 = NAME
    DirectoryObject.thumb = R(ICON)

####################################################################################################
@handler(PREFIX, NAME)
def MainMenu():

    oc = ObjectContainer()

    SHOWS_LIST = CW_SEED_SHOWS+'/genre/shows-a-z'
    html = HTML.ElementFromURL(SHOWS_LIST)
    item_list = html.xpath('//ul[@class="list videos-4up"]/li/a')

    for item in item_list:
        show_url = item.xpath('./@href')[0]
        title = item.xpath('./@data-slug')[0]
        thumb = item.xpath('.//div/img/@data-src')[0].split('//')[-1]
        oc.add(DirectoryObject(
            key=Callback(SeedSeasons, url=show_url, title=title),
            title=title, thumb=thumb
        ))
    # Since this channel contains mostly old shows that will not change,
    # we offer the option of reversing the episode order for continuous play from Preferences
    oc.add(PrefsObject(title="Preferences", summary="Set Episode Order"))
    if len(oc) < 2:
        return ObjectContainer(header='Empty', message='There are currently no seasons for this show')
    else:
        return oc

####################################################################################################
@route(PREFIX + '/seedseasons')
def SeedSeasons(url, title, thumb=''):

    oc = ObjectContainer(title2=title)
    seasons_url = CW_SEED + url
    html = HTML.ElementFromURL(seasons_url)
    if not thumb:
        thumb = html.xpath('//meta[@id="ogimage"]/@content')[0]
    multi_seasons = html.xpath('//div[contains(@id, "seasons-menu2")]/ul/li/a')

    if multi_seasons:
        for item in multi_seasons:
            url = seasons_url + item.xpath('./@href')[0]
            seas_title = item.xpath('.//text()')[0]
            season = int(url.split('?season=')[1].strip())
            oc.add(DirectoryObject(
                key=Callback(SeedJSON, url=url, title=seas_title, show_title=title, season=season),
                title=seas_title, thumb=Resource.ContentsOfURLWithFallback(url=thumb)
            ))
    else:
        oc.add(DirectoryObject(
            key=Callback(SeedJSON, url=url, title="All Videos",
            show_title=title, season=0),
            title="All Videos"
        ))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are currently no seasons for this show')
    else:
        return oc

####################################################################################################
# Pull videos from the json data in the seed formatted video pages
@route(PREFIX + '/seedjson', season=int)
def SeedJSON(url, title, season, show_title):

    oc = ObjectContainer(title2=title)
    content = HTTP.Request(url).content
    html = HTML.ElementFromString(content)
    try:
        json_data = RE_JSON.search(content).group(1)
        json = JSON.ObjectFromString(json_data)
    except:
        return ObjectContainer(header="Empty", message="No json data to pull videos")

    for video in json:
        video_url = CW_ROOT + json[video]['url']
        try:
            duration = int(json[video]['dm'].replace('min', ''))
        except:
            duration = 0
        # The guid number is used to pull images from the html
        try:
            video_thumb = html.xpath(
                '//li[@data-videoguid="%s"]//img/@data-src' % video)[0]
        except:
            video_thumb = None
        episode = json[video]['en'].replace('.', '').strip()
        show = json[video]['st'].strip()
        if episode.isdigit():
            if len(str(season)) > 1:
                season_num = int(episode[0] + episode[1])
            else:
                season_num = int(episode[0])
            episode = int(episode)
        else:
            season_num = 0
            episode = 0
        # Skip videos for other shows
        if show != show_title:
            continue

        oc.add(EpisodeObject(
            show=show,
            season=season_num,
            index=en,
            duration=duration * 60000,
            url=video_url,
            title=json[video]['eptitle'],
            summary=json[video]['d'],
            thumb=Resource.ContentsOfURLWithFallback(url=video_thumb)
        ))

    # For some reason the json is being sorted out of order so we have to sort it here
    # Prefs do not work currently in latest apps
    sort_order = Prefs['sort_order'] if Prefs['sort_order'] in (
        True, False) else True
    oc.objects.sort(key=lambda obj: obj.index, reverse=sort_order)

    if len(oc) < 1:
        Log('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list.")
    else:
        return oc
