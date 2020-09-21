#!/usr/bin/python3
# ebisu-bench: import Anki cards into ebisu's scheduler
# Copyright (C) 2020 Aleksa Sarai <cyphar@cyphar.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import sqlite3
import zipfile
import argparse
import datetime
import tempfile
import collections

from ebisu import ebisu

def get_all_card_ids(conn):
	c = conn.cursor()
	rows = c.execute("SELECT DISTINCT id FROM cards")
	return [card_id for (card_id,) in rows]


def get_review_log(conn, card_id):
	c = conn.cursor()
	rows = c.execute("SELECT id, ease FROM revlog WHERE cid = ?", (card_id,))

	reviews = collections.defaultdict(list)
	for timestamp, button in rows:
		timestamp //= 1000 # switch to seconds
		passed = (button != 1) # (1 = again, 2 = hard, 3 = good, 4 = easy)
		reviews[timestamp].append(passed)
	return sorted(reviews.items())


def open_db(path):
	return sqlite3.connect("file:%s?mode=ro" % (path,), uri=True)


def extract_db(anki_zip):
	tmpfd, db_path = tempfile.mkstemp(prefix="ebisu-bench-ankidb.")
	with zipfile.ZipFile(anki_zip) as zf:
		try:
			info = zf.getinfo("collection.anki2")
		except KeyError:
			raise Exception("anki database invalid -- no collection.anki2 found!")
		with zf.open(info) as zipfh:
			with os.fdopen(tmpfd, "wb") as tmpfh:
				tmpfh.write(zipfh.read())
	return db_path


class EbisuCard(object):
	"Basic representation of Ebisu's model of a card."

	# Identifying and historical information.
	card_id = None
	review_log = None

	# Ebisu model parameters.
	model = None
	last_review = None

	def __init__(self, card_id):
		self.card_id = card_id

	def recall_at(self, tnow=None):
		if tnow is None:
			tnow = int(datetime.datetime.utcnow().timestamp())
		return ebisu.predictRecall(self.model, tnow, exact=True)

	def recall_when(self, percentile=0.50):
		return ebisu.modelToPercentileDecay(self.model, percentile)

	@classmethod
	def emulate(cls, card_id, review_log):
		"Given a card_id the review log for a card, emulate its Ebisu model."

		# Anki assumes all cards have a 10-minute half-life (assuming default
		# learning intervals). So start with that as the Ebisu model.
		current = ebisu.defaultModel(10 * 60)
		last_review = None
		for timestamp, trials in review_log:
			# We need to have a "last review time" to evolve the model.
			if last_review is None:
				# Only take the first successful review as the starting point.
				if any(trials):
					last_review = timestamp
				continue
			tnow = timestamp - last_review
			last_review = timestamp

			# TODO: Deal with numerical instability.
			current = ebisu.updateRecall(current, sum(trials), len(trials), tnow)

		# XXX: We only care about cards that have been reviewed.
		if last_review is None:
			return None

		# Fill model.
		card = cls(card_id)
		card.model = current
		card.review_log = review_log
		card.last_review = last_review
		return card


def fuzzy_delta(dt, raw=False):
	units = [
		("year", 60 * 60 * 24 * 365),
		("month", 60 * 60 * 24 * 30),
		("week", 60 * 60 * 24 * 7),
		("day", 60 * 60 * 24),
		("hour", 60 * 60),
		("minute", 60),
		("second", 1),
	]

	if dt == 0:
		return "now"

	for name, interval in units:
		# Use the interval if dt is larger than one whole interval.
		if abs(dt) < 2 * interval and interval != 1:
			continue

		periods = abs(dt) // interval
		fuzzy = "about %d %s%s" % (
			periods, name, "s" if periods > 1 else "",
		)
		break

	if not raw:
		if dt > 0:
			fuzzy = "in %s" % (fuzzy,)
		elif dt < 0:
			fuzzy = "%s ago" % (fuzzy,)
	return fuzzy


def main(args):
	db_path = extract_db(args.deck)

	# Get list of card_ids to emulate.
	with open_db(db_path) as db:
		card_ids = get_all_card_ids(db)

		total_cards = 0
		total_reviews = 0

		for card_id in card_ids:
			review_log = get_review_log(db, card_id)
			card = EbisuCard.emulate(card_id, review_log)

			if card is None:
				continue

			total_cards += 1
			total_reviews += len(review_log) - 1 # TODO: This is a bit dodgy.

			if args.verbose:
				tnow = datetime.datetime.utcnow().timestamp() - card.last_review
				print("card[%d] (%.2f%% recall now, %s later) will have 85%% recall %s." % (
					card_id, card.recall_at(tnow=tnow) * 100,
					fuzzy_delta(tnow, raw=True),
					fuzzy_delta(card.recall_when(0.85) - tnow),
				))
			elif total_cards % 100 == 0:
				sys.stderr.write(".")
				sys.stderr.flush()

	if not args.verbose:
		sys.stderr.write(" done!\n")

	print("Imported %d cards with %d reviews (~%.1f/card)." % (total_cards, total_reviews, total_reviews / total_cards))
	os.remove(db_path)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--deck", required=True)
	parser.add_argument("--verbose", const=True, action="store_const")

	args = parser.parse_args()
	main(args)
