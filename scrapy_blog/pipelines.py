# -*- coding: utf-8 -*-
import pymysql
import json
import codecs
from scrapy import Request
from scrapy_blog.settings import MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD, MYSQL_DBNAME
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem
from scrapy_blog.log import msg


# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

class ScrapyBlogPipeline(object):

    # 初始化mysql服务
    def __init__(self):
        self.db = pymysql.connect(MYSQL_HOST, MYSQL_USERNAME, MYSQL_PASSWORD, MYSQL_DBNAME)
        self.cursor = self.db.cursor()

    # 持久化数据到数据库中
    def process_item(self, item, spider):

        # 查询数据库中是否存在该数据
        query = "SELECT * from spider_article WHERE title='" + item['title'] + "'"
        self.cursor.execute(query)
        article = self.cursor.fetchall()
        if article:
            return "数据库中已存在该文章:" + item['title']

        item = self.correct_item(item)

        # 插入数据库中去
        insert = "INSERT INTO spider_article " \
                 "(`author`, `clicks`, `content`,  `create_time`, `describe`, `head_img`, `praise`, `title`, `url`,`cover_img`,`source`)\
        VALUES ('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
                 % (item['author'], item['clicks'], pymysql.escape_string(item['content']), item['create_time'],
                    item['describe'], item['head_img'], item['praise'], item['title'], item['url'], item['cover_img'],
                    item['source'])
        try:
            self.cursor.execute(insert)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            return e
        msg(item['title'], '入库成功')
        return item['title']

    # 修正数据
    def correct_item(self, item):

        website = 'https://cdn.99php.cn'

        # 替换文章图片
        if item['article_img_list'] and len(item['article_img_list']) > 0:
            for index, article_img in enumerate(item['article_img_list']):
                correct_article_img = website + '/image/' + item['article_img_paths'][index]
                item['content'] = item['content'].replace(article_img, correct_article_img)

        # 获取替换的头像地址
        if not item['head_img_paths']:
            item['head_img'] = ''
        else:
            item['head_img'] = website + '/image/' + item['head_img_paths'][0]

        # 获取文章封面
        if not item['article_img_paths']:
            item['cover_img'] = ''
        else:
            item['cover_img'] = website + '/image/' + item['article_img_paths'][0]

        return item


# 下载头像图片
class DownloadHeadImagesPipeline(ImagesPipeline):
    # 下载图片
    def get_media_requests(self, item, info):
        if item['head_img'] != '':
            yield Request(item['head_img'])
        else:
            item['head_img_paths'] = []
            return item

    def item_completed(self, results, item, info):
        img_paths = [x['path'] for ok, x in results if ok]
        if not img_paths:
            item['head_img_paths'] = []
        else:
            item['head_img_paths'] = img_paths
        return item


# 下载文章图片
class DownloadArticleImagesPipeline(ImagesPipeline):
    # 下载图片
    def get_media_requests(self, item, info):
        if item['article_img_list']:
            for article_img in item['article_img_list']:
                yield Request(article_img)
        else:
            return item

    def item_completed(self, results, item, info):
        img_paths = [x['path'] for ok, x in results if ok]
        if not img_paths:
            item['article_img_paths'] = []
        else:
            item['article_img_paths'] = img_paths
        return item
