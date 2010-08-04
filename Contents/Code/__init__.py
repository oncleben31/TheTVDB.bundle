import re, unicodedata

TVDB_API_KEY    = 'D4DDDAEFAD083E6F'
TVDB_MIRROR_URL = 'http://thetvdb.com/api/%s/mirrors.xml' % TVDB_API_KEY
TVDB_SEARCH_URL = 'http://thetvdb.com/api/GetSeries.php?seriesname=%s&language=%s'
TVDB_ADVSEARCH_TVCOM  = 'http://thetvdb.com/index.php?seriesname=&fieldlocation=2&genre=&year=&network=&zap2it_id=&tvcom_id=%s&imdb_id=&order=translation&searching=Search&tab=advancedsearch&language=%s'
TVDB_ADVSEARCH_IMDB  = 'http://thetvdb.com/index.php?seriesname=&fieldlocation=2&genre=&year=&network=&zap2it_id=&tvcom_id=&imdb_id=%s&order=translation&searching=Search&tab=advancedsearch&language=%s'
TVDB_ADVSEARCH_NETWORK  = 'http://thetvdb.com/index.php?seriesname=%s&fieldlocation=1&genre=&year=%s&network=%s&zap2it_id=&tvcom_id=&imdb_id=&order=translation&searching=Search&tab=advancedsearch&language=%s'

TVDB_SERIES_URL = '%%s/api/%s/series/%%s' % TVDB_API_KEY
TVDB_ZIP_URL    = '%s/all/%%s.zip' % TVDB_SERIES_URL
TVDB_SERIES_URL = '%s/%%s.xml' % TVDB_SERIES_URL
TVDB_BANNER_URL = '%s/banners/'

GOOGLE_JSON_TVCOM = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&rsz=large&q=inurl:show+inurl:summary.html+site:tv.com+%s'   #[might want to look into language/country stuff at some point] param info here: http://code.google.com/apis/ajaxsearch/documentation/reference.html
GOOGLE_JSON_TVDB = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&rsz=large&q=%s+"thetvdb.com"+series+%s'
GOOGLE_JSON_TVDB_TITLE = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&rsz=large&q=%s+"thetvdb.com"+series+info+%s'
GOOGLE_JSON_BROAD = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&rsz=large&q=%s+site:thetvdb.com+%s'
GOOGLE_JSON_IMDB = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&rsz=large&q=%s+site:imdb.com+tv+%s'

BING_JSON_TVDB = 'http://api.bing.net/json.aspx?AppId=879000C53DA17EA8DB4CD1B103C00243FD0EFEE8&Version=2.2&Query=%s+"series+info"+site:thetvdb.com+%s&Sources=web&Web.Count=8&JsonType=raw'
BING_JSON_TVDB_TITLE = 'http://api.bing.net/json.aspx?AppId=879000C53DA17EA8DB4CD1B103C00243FD0EFEE8&Version=2.2&Query=%s+intitle:"series+info"+site:thetvdb.com+%s&Sources=web&Web.Count=8&JsonType=raw'
BING_JSON_TVCOM ='http://api.bing.net/json.aspx?AppId=879000C53DA17EA8DB4CD1B103C00243FD0EFEE8&Version=2.2&Query=%s+site:tv.com+%s&Sources=web&Web.Count=8&JsonType=raw'

TVRAGE_SEARCH   = 'http://services.tvrage.com/feeds/search.php?show=%s' 

SCRUB_FROM_TITLE_SEARCH_KEYWORDS = ['uk','us']
NETWORK_IN_TITLE = ['bbc']
EXTRACT_AS_KEYWORDS = ['uk','us','bbc']

def Start():
  """
    Fetch the list of mirrors from TheTVDB and pick a zip and image mirror at random.
  """
  mirrors_el = XML.ElementFromURL(TVDB_MIRROR_URL, cacheTime = CACHE_1MONTH)
  
  zip_mirrors = []
  img_mirrors = []
  
  # Compare the type mask of each mirror to check what type of data it provides
  for mirror in mirrors_el.xpath('Mirror'):
    try:
      typemask = int(mirror.xpath('typemask')[0].text)
      path = mirror.xpath('mirrorpath')[0].text
      if typemask & 4:
        zip_mirrors.append(path)
      if typemask & 2:
        img_mirrors.append(path)
    except:
      print Plugin.Traceback()
      
  Dict['ZIP_MIRROR'] = Util.RandomItemFromList(zip_mirrors)
  Dict['IMG_MIRROR'] = Util.RandomItemFromList(img_mirrors)
  
  HTTP.CacheTime = CACHE_1DAY
  
class TVDBAgent(Agent.TV_Shows):
  
  name = 'TheTVDB'
  languages = [Locale.Language.English]
  
  def search(self, results, media, lang):
    
    # MAKE SURE WE USE precomposed form, since that seems to be what TVDB prefers.
    media.show = unicodedata.normalize('NFC', unicode(media.show))
    
    mediaYear = ''
    if media.year is not None:
      mediaYear = ' (' + media.year + ')'
    w = media.show.lower().split(' ')
    keywords = ''
    for k in EXTRACT_AS_KEYWORDS:
      if k.lower() in w:
        keywords = keywords + k + '+'
    cleanShow =  self.util_cleanShow(media.show, SCRUB_FROM_TITLE_SEARCH_KEYWORDS)
    cs = cleanShow.split(' ')
    cleanShow = ''
    for x in cs:
      cleanShow = cleanShow + 'intitle:' + x + ' '
      
    cleanShow = cleanShow.strip()
    origShow = media.show
    SVmediaShowYear = {'normal':String.Quote((origShow + mediaYear).encode('utf-8'), usePlus=True).replace('intitle%3A', 'intitle:'),
                       'clean': String.Quote((cleanShow + mediaYear).encode('utf-8'), usePlus=True).replace('intitle%3A','intitle:')}
    mediaShowYear = SVmediaShowYear['normal']
    
    searchVariations = [SVmediaShowYear]
    if media.year is not None:
      SVmediaShow = {'normal':String.Quote((origShow).encode('utf-8'), usePlus=True).replace('intitle%3A', 'intitle:'),
                     'clean': String.Quote((cleanShow).encode('utf-8'), usePlus=True).replace('intitle%3A', 'intitle:')}
      searchVariations.append(SVmediaShow)
    
    #option to perform searches without the year, in the event we have no results over our match threshold
    for sv in searchVariations:
      #check to make sure we want to run these searches again WITHOUT the year hint, if there was one passed in
      if len(results) > 0:
        results.Sort('score', descending=True)
        if results[0].score >= 80:
          break #don't bother trying search without year, we have a match
          
      #run through several search engines
      resultDict = {}
      @parallelize
      def hitSearchEngines():
        for s in [BING_JSON_TVCOM, BING_JSON_TVDB, GOOGLE_JSON_TVDB, BING_JSON_TVDB_TITLE, GOOGLE_JSON_TVDB_TITLE, GOOGLE_JSON_IMDB, GOOGLE_JSON_BROAD]: #
          resultDict[s] = []
          @task
          def UpdateEpisode(s=s,sv=sv):
            hasResults = False
            if s in [BING_JSON_TVDB_TITLE, GOOGLE_JSON_TVDB_TITLE]:
              tmpMediaShowYear = sv['clean'] #String.Quote((cleanShow + mediaYear).encode('utf-8'), usePlus=True).replace('intitle%3A','intitle:')
            else:
              tmpMediaShowYear = sv['normal']
            #make sure we have results and normalize
            if s.count('bing.net') > 0:
              jsonObj = JSON.ObjectFromURL(s % (tmpMediaShowYear, keywords))['SearchResponse']['Web']
              if jsonObj['Total'] > 0:
                jsonObj = jsonObj['Results']
                hasResults = True
            elif s.count('googleapis.com') > 0:
              jsonObj = JSON.ObjectFromURL(s % (tmpMediaShowYear, keywords))['responseData']['results']
              if len(jsonObj) > 0:
                hasResults = True
  
            #loop through results   
            if hasResults:
              for r in jsonObj:
                scorePenalty = 0
                url = None
                if s == BING_JSON_TVCOM:
                  TVurl = r['Url'].split('\/')
                  if len(TVurl) == 1:
                    TVurl = r['Url'].split('/')
                  if TVurl[-3] == 'show':
                    tvID = TVurl[-2]  
                    try:
                      url = HTML.ElementFromURL(TVDB_ADVSEARCH_TVCOM % (tvID, lang)).xpath('//table[@id="listtable"]//tr[2]//a')[0].get('href')
                      scorePenalty = -5
                    except:
                      return
                  else:
                    return
                elif s.count('googleapis.com') > 0:
                  url = r['unescapedUrl']
                elif s.count('bing.net') > 0:
                  url = r['Url']
            
                if url:
                  resultDict[s].append((url, scorePenalty))
            
      @parallelize
      def loopResults():
        for s in resultDict:  
          if s == BING_JSON_TVCOM:
            score = 93
          elif s in [GOOGLE_JSON_TVDB, BING_JSON_TVDB, GOOGLE_JSON_IMDB, BING_JSON_TVDB_TITLE, GOOGLE_JSON_TVDB_TITLE, GOOGLE_JSON_BROAD]:
            score == 99
          else:
            break
          for url, scorePenalty in resultDict[s]:          
            @task
            def lookupResult(score=score, url=url, scorePenalty=scorePenalty):
              self.TVDBurlParse(media, lang, results, score, scorePenalty, url)
            score = score - 5
      
    #try an exact tvdb match    
    try:
      el = XML.ElementFromURL(TVDB_SEARCH_URL % (mediaShowYear, lang)).xpath('.//Series')[0]
      series_name = el.xpath('SeriesName')[0].text
      if series_name.lower() == media.show.lower():
        id = el.xpath('id')[0].text
        self.ParseSeries(media, el, lang, results, 99)
    except:
      pass
    
    #try advanced tvdb search
    #first see if we have any networks in title
    networks = ''
    w = media.show.lower().split(' ')
    for k in NETWORK_IN_TITLE:
      if k.lower() in w:
        networks = networks + k + '+'
    searchForTitle =  self.util_cleanShow(media.show, SCRUB_FROM_TITLE_SEARCH_KEYWORDS + NETWORK_IN_TITLE)
    ADVscore = 99
    year= ''
    if year:
      year = str(media.year)
    try:
      for el in  HTML.ElementFromURL(TVDB_ADVSEARCH_NETWORK % (searchForTitle, year, networks[:-1], lang)).xpath('//table[@id="listtable"]//tr')[1:10]:
        url = el.xpath('.//a')[0].get('href').replace('&amp;','&')
        self.TVDBurlParse(media, lang, results, ADVscore, 0, url)
        ADVscore = ADVscore - 1
    except:
      pass
          
    #run through tvRage -> tvdb name matches. the challenge with this is that it can only help a little...there is no tvrage->thetvdb lookup today.
    score = 100
    try:
      for r in XML.ElementFromURL(TVRAGE_SEARCH % mediaShowYear).xpath('//show')[:4]:
        score = score - 3
        tvrageName = r.xpath('name')[0].text
        tvrageLink = r.xpath('link')[0].text
        network = HTML.ElementFromURL(tvrageLink).xpath('//a[contains(@href,"/networks")]')[0].text_content()
        #Log("****************" + network  )
        try:
          ADVscore = 100
          year= ''
          if year:
            year = str(media.year)
          #will need to get the whole tvdb language mapping in here:  
          if lang == 'en':
            tvdbLang = '7'
          try:
            for el in  HTML.ElementFromURL(TVDB_ADVSEARCH_NETWORK % (String.Quote(searchForTitle), year, String.Quote(network), tvdbLang)).xpath('//table[@id="listtable"]//tr')[1:3]:
              url = el.xpath('.//a')[0].get('href').replace('&amp;','&')
              self.TVDBurlParse(media, lang, results, ADVscore, 0, url)
              ADVscore = ADVscore - 5
          except:
            pass
        except:
          pass
    except:    
      Log('TVRage fetch error. Timeout?')
      pass
       
    results.Sort('score', descending=True)

    # de-dupe the results.
    toWhack = []
    resultMap = {}
    for result in results:
      if not resultMap.has_key(result.id):
        resultMap[result.id] = True
      else:
        toWhack.append(result)    
    for dupe in toWhack:
      results.Remove(dupe)
    
    favorNewerShows = True
    if favorNewerShows:  
      #hunt for duplicate shows with different years
      resultMap = {}
      for result in results:
        for check in results:
          if result.name == check.name and result.id != check.id:
            resultMap[result.year] = result
          
      years = resultMap.keys()
      years.sort(reverse=True)
    
      #bump the score of newer dupes
      i=0
      for y in years[:-1]:
        if resultMap[y].score <= resultMap[years[i+1]].score:
          resultMap[y].score = resultMap[years[i+1]].score + 1
          
      #for result in results:
      #  Log(result.name + ' ('+ result.id +') score: ' + str(result.score))
  
  def TVDBurlParse(self, media, lang, results, score, scorePenalty, url):
    if url.count('tab=series&id='):
      seriesRx = 'tab=series&id=([0-9]+)'
      m = re.search(seriesRx, url)  
    elif url.count('tab=seasonall&id='):
      seriesRx = 'tab=seasonall&id=([0-9]+)'
      m = re.search(seriesRx, url)
    else:
      seriesRx = 'seriesid=([0-9]+)'
      m = re.search(seriesRx, url)
    if m:
      id = m.groups(1)[0]
      try:
        xml = XML.ElementFromURL(TVDB_SERIES_URL % (Dict['ZIP_MIRROR'], id, lang))
        if len(xml):
          self.ParseSeries(media, xml.xpath('//Series')[0], lang, results, score - scorePenalty)
      except:
        #somehow the tvdb id didn't work?
        Log('thetvdb.com series xml download exception.')
      
  def ParseSeries(self, media, el, lang, results, score):
    
    # Get attributes from the XML
    try:
      series_id = el.xpath('seriesid')[0].text
    except:
      series_id = el.xpath('id')[0].text
      
    series_name = el.xpath('SeriesName')[0].text
    try:
      series_year = el.xpath('FirstAired')[0].text[:4]
    except:
      series_year = None
      
    try:
      series_lang = el.xpath('language')[0].text
    except:
      series_lang = lang
      
    if not series_name:
      return

    if not media.year:
      clean_series_name = series_name.replace('(' + str(series_year) + ')','').strip().lower()
    else:
      clean_series_name = series_name.lower()

    cleanShow = self.util_cleanShow(media.show, NETWORK_IN_TITLE)
      
    #Log(media.show + ' | found: ' + series_name + ' score1: +[original] ' + str(score))
    
    substringLen = len(Util.LongestCommonSubstring(cleanShow.lower(), clean_series_name))
    cleanShowLen = len(cleanShow)
    
    maxSubstringPoints = 5.0 #use a float
    score = score + int((maxSubstringPoints * substringLen)/cleanShowLen) # max 15 for best substring match
    #Log(media.show + ' | found: ' + series_name + ' score2: +[longest substring]: ' + str(score))
    
    distanceFactor = .6
    score = score - int(distanceFactor * Util.LevenshteinDistance(cleanShow.lower(), clean_series_name))
    #Log(media.show + ' | found: ' + series_name + ' score3: +[levenshteindistance]: ' + str(score))
    
    if series_year and media.year:
      if media.year == series_year: 
        score = score + 10
      else:
        score = score - 10
    
    #sanity check to make sure we have SOME common substring
    if (float(substringLen) / cleanShowLen) < .15: #if we don't have at least 15% in common, then penalize below the 80 point threshold
      score = score - 25
      
    #Log(media.show + ' | found: ' + series_name + ' score4: +[year match]: ' + str(score))
    
    # Add a result for this show
    results.Append(
      MetadataSearchResult(
        id    = series_id,
        name  = series_name,
        year  = series_year,
        lang  = series_lang,
        score = score
      )
    )

  def readTags(self, element, list, name):
    try:
      el_text = lambda element, xp: element.xpath(xp)[0].text
      tag_text = el_text(element, name)
      if tag_text.find('|') != -1:
        tags = tag_text.split('|')
      else:
        tags = tag_text.split(',')
      
      tags = [tag.strip() for tag in tags if len(tag) > 0]
      list.clear()
      for tag in tags:
        if tag not in list:
          list.add(tag)
    except:
      pass

  def update(self, metadata, lang):
    zip_url = TVDB_ZIP_URL % (Dict['ZIP_MIRROR'], metadata.id, lang)
    banner_root = TVDB_BANNER_URL % Dict['IMG_MIRROR']
    
    # Get the show's zipped data
    zip_data = HTTP.Request(zip_url)
    zip_archive = Archive.Zip(zip_data)
    
    # Extract the XML files from the archive
    root_el = XML.ElementFromString(zip_archive[lang+'.xml'])
    actors_el = XML.ElementFromString(zip_archive['actors.xml'])
    banners_el =XML.ElementFromString(zip_archive['banners.xml'])
    
    # Close the archive
    del zip_archive
    
    # Get the root element
    series_el = root_el.xpath('Series')[0]
    
    # Convenience functions
    el_text = lambda element, xp: element.xpath(xp)[0].text if element.xpath(xp)[0].text else '' 
    parse_date = lambda s: Datetime.ParseDate(s).date()
    
    # Copy attributes from the XML element to the metadata object
    metadata.name = el_text(series_el, 'SeriesName')
    metadata.description = el_text(series_el, 'Overview')
    metadata.content_rating = el_text(series_el, 'ContentRating')
    metadata.studio = el_text(series_el, 'Network')
    try: 
      first_aired = el_text(series_el, 'FirstAired')
      if len(first_aired) > 0:
        metadata.originally_available_at = parse_date(first_aired)
      else:
        metadata.originally_available_at = None
    except: pass
    try: metadata.runtime = int(el_text(series_el, 'Runtime')) * 60 * 1000
    except: pass
    try: metadata.community_rating = float(el_text(series_el, 'Rating'))
    except: pass
    
    self.readTags(series_el, metadata.genres, 'Genre')
    
    # Get episode data
    @parallelize
    def UpdateEpisodes():

      for episode_el in root_el.xpath('Episode'):
        
        # Get the season and episode numbers
        season_num = el_text(episode_el, 'SeasonNumber')
        episode_num = el_text(episode_el, 'EpisodeNumber')
        
        # Get the episode object from the model
        episode = metadata.seasons[season_num].episodes[episode_num]
        
        # Create a task for updating this episode
        @task
        def UpdateEpisode(episode=episode, episode_el=episode_el):        

          # Copy attributes from the XML
          episode.title = el_text(episode_el, 'EpisodeName')
          episode.description = el_text(episode_el, 'Overview')
          
          try: episode.absolute_number = int(el_text(episode_el, 'absolute_number'))
          except: pass
      
          rating = el_text(episode_el, 'Rating')
          if rating != None and len(rating) > 0: episode.community_rating = float(rating)
          
          try:    
            first_aired = el_text(episode_el, 'FirstAired')
            if first_aired != None and len(first_aired) > 0: 
              episode.originally_available_at = parse_date(first_aired)
          except:
            pass  
          
          self.readTags(episode_el, episode.directors, 'Director')
          self.readTags(episode_el, episode.writers, 'Writer')
          
          # Download the episode thumbnail
          if len(episode_el.xpath('filename')) > 0:
            thumb_file = el_text(episode_el, 'filename')
            if thumb_file != None and len(thumb_file) > 0:
              thumb_url = banner_root + thumb_file
              thumb_data = HTTP.Request(thumb_url)
              
              # Check that the thumb doesn't already exist before downloading it
              if thumb_url not in episode.thumbs:
                try:
                  episode.thumbs[thumb_url] = Proxy.Media(thumb_data)
                except:
                  # tvdb doesn't have a thumb for this show
                  pass
      
    @parallelize
    def DownloadImages():

      # Add a download task for each image
      i = 0
      for banner_el in banners_el.xpath('Banner'):
        i += 1
        @task
        def DownloadImage(metadata=metadata, banner_el=banner_el, i=i):
          
          # Get the image attributes from the XML
          banner_type = el_text(banner_el, 'BannerType')
          banner_path = el_text(banner_el, 'BannerPath')
          try:
            banner_thumb = el_text(banner_el, 'ThumbnailPath')
            proxy = Proxy.Preview
          except:
            banner_thumb = banner_path
            proxy = Proxy.Media
          banner_lang = el_text(banner_el, 'Language')
          
          # Check that the language matches
          if banner_lang != lang:
            return
            
          # Compute the banner name and prepare the data
          banner_name = banner_root + banner_path
          banner_data = HTTP.Request(banner_root + banner_thumb)
        
          # Find the attribute to add to based on the image type, checking that data doesn't
          # already exist before downloading
          if banner_type == 'fanart' and banner_name not in metadata.art:
            try: metadata.art[banner_name] = proxy(banner_data, sort_order=i)
            except: pass

          elif banner_type == 'poster' and banner_name not in metadata.posters:
            try: metadata.posters[banner_name] = proxy(banner_data, sort_order=i)
            except: pass

          elif banner_type == 'series':
            if banner_name not in metadata.banners:
              try: metadata.banners[banner_name] = proxy(banner_data, sort_order=i)
              except: pass

          elif banner_type == 'season':
            banner_type_2 = el_text(banner_el, 'BannerType2')
            season_num = el_text(banner_el, 'Season')
          
            if banner_type_2 == 'season' and banner_name not in metadata.seasons[season_num].posters:
              try: metadata.seasons[season_num].posters[banner_name] = proxy(banner_data, sort_order=i)
              except: pass

            elif banner_type_2 == 'seasonwide' and banner_name not in metadata.seasons[season_num].banners:
              try: metadata.seasons[season_num].banners[banner_name] = proxy(banner_data, sort_order=i)
              except: pass
              
  def util_cleanShow(self, cleanShow, scrubList):
    for word in scrubList:
      c = word.lower()
      l = cleanShow.lower().find('(' + c + ')')
      if l >= 0:
        cleanShow = cleanShow[:l] + cleanShow[l+len(c)+2:]
      l = cleanShow.lower().find(' ' + c)
      if l >= 0:
        cleanShow = cleanShow[:l] + cleanShow[l+len(c)+1:]
      l = cleanShow.lower().find(c + ' ')
      if l >= 0:
        cleanShow = cleanShow[:l] + cleanShow[l+len(c)+1:]
    return cleanShow
      