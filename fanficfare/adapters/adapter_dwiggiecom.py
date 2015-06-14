# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import time
import logging
import re
import urllib2

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return DwiggieComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class DwiggieComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["Windows-1252",
                       "utf8"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        self.sectionUrl = ""
        self.section = []
        self.chapters = dict()

        
#        # get storyId from url--url validation guarantees query is only sid=1234
#        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
#        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
                
                
                  # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
            # normalized story URL.
            self._setURL('http://www.' + self.getSiteDomain() + '/derby/'+self.story.getMetadata('storyId')+'.htm')
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','dwg')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'dwiggie.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.dwiggie.com','dwiggie.com']

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/derby/name1b.htm"

    def getSiteURLPattern(self):
        # http://www.dwiggie.com/derby/mari17b.htm
        return re.escape("http://")+"(www.)?"+re.escape(self.getSiteDomain())+r"/derby/(?P<id>(old_\d{4}\/)?[a-z]+\d+)(?P<part>[a-z]*)\.htm$"     
        
    def tryArchivePage(self, url):
        
        try:
            data = self._fetchUrl(url)
      
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.meta)           # need to change the exception returned
            else:
                raise e
      
        archivesoup = bs.BeautifulSoup(data)
        m = re.compile(r"/derby/"+self.story.getMetadata('storyId')+"[a-z]?.htm$")
        #print m.pattern
        #print archivesoup
        a = archivesoup.find('a', href=m)               #http://www.indeath.net/user/9083-cyrex/
        
        return a
    
    def getGenre(self, url):
        if re.search('id=E',url):
            genre='Epilogue Abbey'
        else:
            genre='Fantasia Gallery'
        self.story.addToList('genre',genre)
        
    def getItemFromArchivePage(self):
        
        urls = ["http://www.dwiggie.com/toc/index.php?id=E&page=all&comp=n","http://www.dwiggie.com/toc/index.php?id=F&page=all&comp=n"]
        for url in urls:
            a = self.tryArchivePage(url)
            if a != None:
                self.getGenre(url)
                return a.parent
        else:
            return None
                    
                    
    def getMetaFromSearch(self):
        
        params = {}
        params['title_name'] = self.story.getMetadata('title')
        
        searchUrl = "http://" + self.getSiteDomain() + "/toc/search.php"
        
        d = self._postUrl(searchUrl, params)
        #print d
        
        searchsoup = bs.BeautifulSoup(d)
        m = re.compile(r"/derby/"+self.story.getMetadata('storyId')+"[a-z]?.htm$")
        #print m.pattern
        #print self.story.getMetadata('storyId')
        a = searchsoup.find('a', href=m)                #http://www.indeath.net/user/9083-cyrex/

        return a
        
        
    def getChaptersFromPage(self, url):
        data = self._fetchUrl(url)
        
        s = self.story.getMetadata('storyId').split('/')
        s.reverse()
        storyId_trimmed = s[0]
                
        # Get just the relevant page content without body tags etc.
        m = re.match('.*?<body[^>]*>(\s*<ul>)?(?P<content>.*?)</body>', data, re.DOTALL)
        newdata = m.group('content')
        
        # Get rid of Next/Previous section links at the top
        regex=re.compile(r'<a\ href\=\"'+storyId_trimmed+'[a-z]?.htm\">(Continued\ [Ii]n\ )?(the\ )?[Nn]ext\ [Ss]ection</a>')
        newdata = re.sub(regex, '', newdata)

        
        # split on hr with no attributes and drop empty sections
        pagesections = filter(lambda x:x!=None, re.split('<hr( \/)?>', newdata)) 
        
        # additional filtering (can't remember for what case...)                      
        pagesections = filter(lambda x:x.strip()!='/', pagesections)
                    
        # always remove header
        pagesections.pop(0)     
        
        # Get rid of sections with Next/Previous section links or copywrite notices (at the end)
        regex = re.compile(r'(?m)(href\="'+storyId_trimmed+'[a-z]?.htm\"|Copyright\ held\ by\ the\ author|<p>\s*(Section\ I|Beginning),\s*</?p>)', re.MULTILINE)
        pagesections = filter(lambda x: not regex.search(x), pagesections)

        # drop sections where the text (after stripping tags) is less than 5 characters - that is not a chapter.
        pagesections = [i for i in pagesections if len(i.strip()) >= 5]  
    
        return pagesections  
                

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        meta = self.getItemFromArchivePage()
        #print meta
       
        # Title
        t = meta.a
        self.story.setMetadata('title',t.string.strip())
                
        # Author
        author = meta.find('a','author_link')
        if author != None:
            self.story.setMetadata('author',author.string.strip())
            self.story.setMetadata('authorId',author['href'].split('=')[1])
            self.story.setMetadata('authorUrl',author['href'])
            author=author.parent
        else:
            author=meta.i
            self.story.setMetadata('author',author.string.replace('Written by','').strip())
            self.story.setMetadata('authorId','unknown')
            self.story.setMetadata('authorUrl','unknown')
           

        # DateUpdated
        dUpdate = meta.find('i',text = re.compile('Last update'))
        du = dUpdate.replace('Last update','').replace('.','').strip()
        self.story.setMetadata('dateUpdated', makeDate(du, self.dateformat))
        compImg=meta.find('img',alt="Dot")
        if compImg != None:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')


        # Summary & Category
        # Get the summary components from the meta listing        
        metalist=meta.contents
        s=[]
        for x in xrange(0,len(metalist)-1):
            item=metalist[x]
            if item==author or item==compImg:
                s=[]
                continue
            if item==dUpdate or item==dUpdate.parent:
                break
            s.append(item)            
        
        # create a soup object from the summary components
        soup=bs.BeautifulSoup("<p></p>")
        d=soup.p
        for x in s:
            d.append(x)
        #print d       

        # extract category from summary text
        desc=stripHTML(d)
        books = re.compile(r'(?P<book>\~P&P;?\~|\~Em;?\~|\~MP;?\~|\~S\&S;?\~|\~Per;?\~|\~NA;?\~|\~Juv;?\~|\~Misc;?\~)')
        booklist=dict({'~P&P~':'Pride and Prejudice','~Em~':'Emma','~MP~':'Mansfield Park','~S&S~':'Sense and Sensibility','~Per~':'Persuasion','~NA~':'Northanger Abbey','~Juv~':'Juvenilia','~Misc~':'Miscellaneous'})
        m=re.search(books,desc)
        print m.group('book')
        book=booklist.get(m.group('book').replace(';',''))
        print book
        self.story.addToList('category',book)

        
        # assign summary info
        desc=stripHTML(desc).replace(book,'').strip()
        desc=re.sub('^.\s*','',desc)        
        if desc != None:
            self.setDescription(url,desc)

            
            
     

        ## Chapters (Sections in this case - don't know if we can subdivide them)
        
        # get the last Section from the archive page link 
        #chapters = ["http://www.dwiggie.com"+t['href']]

        # get the section letter from the last page
        m = re.match("/derby/"+self.story.getMetadata('storyId')+"(?P<section>[a-z]?).htm$",t['href'])
        inc = m.group('section')
        if inc == '':
            inc = 'a'

                
        # get the presumed list of section urls with 'lower' section letters
        sections = []
        baseurl = "http://www.dwiggie.com/derby/"+self.story.getMetadata('storyId')
        extension = ".htm"
        ordend = ord(inc)
        ordbegin = ord('a')
        for numinc in xrange(ordbegin,ordend+1):
                inc = chr(numinc)
                if inc == 'a':
                    sections.append(baseurl+extension)
                else:
                    sections.append(baseurl+inc+extension)
            
            

                # Process List of Chapters 
                # create 'dummy' urls for individual chapters in the form 'pageurl#pageindex' where page index is an index starting with 0 per page             
        c = 0
        postdate=None
        chapters = []
        for x in range(0,len(sections)):
            section=sections[x]
            i=0
            for chapter in self.getChaptersFromPage(section):
                c+=1 
                chaptersoup = bs.BeautifulSoup(chapter)
                #self.chapterUrls.append(('Chapter '+str(c),section+'#'+str(i)))
                cUrl = section+'#'+str(i)
                
                # Chapter titles generally have font="+1" color="#336666" but some don't have the last '6' on the color definition
                t = chaptersoup.find('font',size="+1",color=re.compile("#33666"))
                
                # If no matching title section then just use the first non-empty paragraph text if the text length is less than 50 chars
                if t==None:
                    paras = chaptersoup.find_all(text=re.compile("Chapter"))
                    print paras
                    #~ fp = ''
                    #~ for p in chaptersoup.find_all('p'):
                        #~ if stripHTML(p)!=re.compile('^\s*$'):
                            #~ fp = p
                            #~ break
                    #~ 
                    #~ print fp        
                    #~ if len(stripHTML(fp)) < 50:
                        #~ t = fp
                    
                ctitle = ''
                if t!=None:
                    ctitle=stripHTML(t)
                #self.chapterUrls.append(('Chapter '+str(c),cUrl))
                self.chapterUrls.append((ctitle,cUrl))
                chapters.append((cUrl,chaptersoup))
                if postdate==None:
                    regex=re.compile(r'Posted\ on\:?\ (?P<date>\d{4}\-\d{2}\-\d{2}|\w+,\ \d+\ \w+\ \d{4})')
                    #Sunday, 21 March 2004, at 6:00 a.m.
                    m=re.search(regex,chapter)
                    if m!=None:
                        postdate=m.group('date')
                i+=1
        self.chapters=dict(chapters)
        #print postdate
        pubdate=None
        if postdate!=None:
            format1=re.match(re.compile(r'\d{4}\-\d{2}\-\d{2}'),postdate)
            format2=re.match(re.compile(r'\w+,\ \d+\ \w+\ \d{4}'),postdate)
            if format1!=None:
                pubdate = makeDate(postdate, "%Y-%m-%d")
            if format2!=None:
                pubdate = makeDate(postdate, "%A, %d %B %Y")
            
                    
        if pubdate==None:
            pubdate=makeDate(self.story.getMetadata('dateUpdated'), "%Y-%m-%d")
        #print pubdate
        self.story.setMetadata('datePublished', pubdate)   
        #print self.story.getMetadata('dateUpdated')
        #print self.story.getMetadata('datePublished')      
        self.story.setMetadata('numChapters',c)
        logging.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))
        
        
        
    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logging.debug('Getting chapter text from: %s' % url)
        
        chapter = self.chapters.get(url)
#        for c in self.chapters:
#            if c[0] == url:
#                chapter = c[1]
                #chapter = bs.BeautifulSoup(c[1])       
        
        #chapter = find(lambda c: c[0] == url, self.chapters)[1]
#        page_url = url.split('#')[0]
#        x = url.split('#')[1]        
#        if self.sectionUrl != page_url:
#            self.sectionUrl = page_url
#            self.section = self.getChaptersFromPage(page_url)
#        
#        chapter = bs.BeautifulSoup(self.section[int(x)])

        #chapter = bs.BeautifulSoup(self.getChaptersFromPage(page_url)[int(x)])

        return self.utf8FromSoup(url,chapter)