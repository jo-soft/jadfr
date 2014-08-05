from apps.categories.models import Category
from apps.feeds.models import UserFeed
from django.contrib.auth.models import User
from feeds.models import Feed
import opml

__author__ = 'j_schn14'

from optparse import make_option

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--user', '-u', action="store", type="string", dest="user"),
        make_option('--file', '-f', action="store", type="string", dest="filename"),
        make_option('--quiet', '-q', action="store_false", dest="verbose"),
        make_option('--dry-run', '-d', action="store_true", dest="dry_run"),
    )

    def __int__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.user = None

    def handle(self, *args, **options):

        user = options.get('user')
        file_name = options.get('filename')
        verbose = options.get('verbose')
        dry_run = options.get('dry_run')

        self.set_user(user)
        data = self.parse_file(file_name)
        self.save(data, dry_run=dry_run)

    def set_user(self, user):
        self.user = User.objects.get(name=user)

    def parse_file(self, file_name):
        outline = opml.parse(file_name)
        return self.get_feeds_from_outline(outline)

    def get_feeds_from_outline(self, outline):
        result = CategoryInfo(name=outline.title)
        for o in outline:
            values = o._root.find('[@xmlUrl]')
            if values is not None:
                result.add(FeedInfo(
                    feed_type=values.get('type'),
                    feed_url=values.get('xmlUrl'),
                    html_url=values.get('htmlUrl'),
                    title=values.get('title'),
                    category=result
                ))
            else:
                result.add(self.get_feeds_from_outline(o))
        return result

    def save(self, data, dry_run=False):
        for item in data:
            if isinstance(FeedInfo, item):
                save_func = self._save_feed
            else:
                save_func = self._save_category
            save_func(item, dry_run=dry_run)

    def _save_feed(self, feed_item, dry_run):
        try:
            feed = Feed.objects.get(feed_url=feed_item.feed_url, url=feed_item.html_url)
        except Feed.DoesNotExists:
            feed = Feed(
                feed_url=feed_item.feed_url,
                url=feed_item.html_url,
                name=feed_item.title
            )
            if not dry_run:
                feed.save()
        try:
            user_feed = UserFeed.objects.get(feed=feed, user=self.user)
        except UserFeed.DoesNotExists:
            user_feed = UserFeed.objects.create(
                feed=feed,
                user=self.user
            )
        feed_category = Category.objects.get(name=feed_item.category.name)
        user_feed.categories.add(feed_category)
        if not dry_run:
            user_feed.save()

    def _save_category(self, category_item, dry_run):
        if not Category.objects.get(name=category_item.name).exists():
            category = Category(name=category_item.name)
            if not dry_run:
                category.save()
        self.save(category_item)


class FeedInfo(object):
    def __int__(self,
                feed_type,
                feed_url,
                html_url,
                title,
                category
    ):
        self.feed_type = feed_type
        self.feed_url = feed_url
        self.html_url = html_url
        self.title = title
        self.category = category


class CategoryInfo(set):
    name = ''

    def __int__(self, name, **kwargs):
        super(CategoryInfo, self).__init__()
        self.name = name
        if 'items' in kwargs:
            self.add(item for item in kwargs['items'])