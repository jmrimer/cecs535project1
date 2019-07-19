import sys
import unittest

from test_helpers import *
from test_helpers import verify_bidders_are_not_auction_sellers, attempt_bid_on_item_auctioned_by_bidder, \
    fetch_seller_and_auction, verify_deny_seller_bid, verify_all_existing_bids_fall_within_auction_time_windows, \
    verify_valid_bid_insertion_at_auction_start, attempt_bid_before_auction_start, attempt_bid_after_auction_ends


class TestTriggers(unittest.TestCase):
    real_database = None
    trigger_dir = "../src/triggers"

    def setUp(self) -> None:
        # self.conn = connect_to_test_database(self.real_database)
        self.conn = connect_to_test_database('ebay_db')
        self.cursor = self.conn.cursor()

    def tearDown(self) -> None:
        self.conn.close()

    def test_all_triggers_still_allow_happy_path(self):
        add_all_triggers(self.trigger_dir, self.cursor)
        verify_allow_valid_insertion_on_every_table(self, self.cursor)

    def test_new_bid_with_existing_user(self):
        starting_bid_count = count_from_table(self.cursor, 'bid')
        insert_fresh_bid(self.cursor)
        verify_bid_added_to_table(self, self.cursor, starting_bid_count)

    def test_bidding_with_new_user_triggers_user_creation(self):
        add_trigger(self.trigger_dir, self.cursor, 1)
        new_user = generate_new_user(self, self.cursor)
        insert_bid_from_new_user(self.cursor, new_user)
        verify_new_user_created(self, self.cursor, new_user)

    def test_new_auction_with_new_seller_triggers_user_creation(self):
        add_trigger(self.trigger_dir, self.cursor, 2)
        new_seller = generate_new_user(self, self.cursor)
        create_new_auction_from_new_seller(self, self.cursor, new_seller)
        verify_new_user_created(self, self.cursor, new_seller)

    def test_auction_current_price_always_matches_most_recent_bid_for_auction(self):
        add_trigger(self.trigger_dir, self.cursor, 3)
        (
            auction,
            highest_bid_price,
            user_id
        ) = setup_auction_with_beatable_bid(self.cursor)
        verify_insertion_with_exceeding_bid_sets_global_highest_price(
            self,
            self.cursor,
            auction,
            highest_bid_price,
            user_id
        )
        deny_new_bid_with_value_less_than_current_high(
            self,
            self.cursor,
            auction,
            user_id
        )
        current_price_still_matches_highest_bid(
            self,
            self.cursor,
            auction,
            highest_bid_price
        )

    def test_no_bids_belong_to_auction_sellers(self):
        verify_bidders_are_not_auction_sellers(self, self.cursor)

    def test_seller_may_not_bid_on_auction(self):
        add_trigger(self.trigger_dir, self.cursor, 4)
        starting_bid_count = count_from_table(self.cursor, 'bid')
        (
            auction_id,
            seller_id
        ) = fetch_seller_and_auction(self.cursor)
        attempt_bid_on_item_auctioned_by_bidder(
            self,
            self.cursor,
            auction_id,
            seller_id
        )
        verify_deny_seller_bid(
            self,
            self.cursor,
            starting_bid_count
        )

    def test_all_bids_occur_within_auction_start_and_end(self):
        add_trigger(self.trigger_dir, self.cursor, 5)
        user_id = get_existing_user_id(self.cursor)
        (
            auction_end,
            auction_id,
            auction_start
        ) = get_auction(self.cursor)

        verify_all_existing_bids_fall_within_auction_time_windows(
            self,
            self.cursor
        )
        verify_valid_bid_insertion_at_auction_start(
            self,
            self.cursor,
            auction_id,
            auction_start,
            user_id
        )
        attempt_bid_before_auction_start(
            self,
            self.cursor,
            auction_id,
            auction_start,
            user_id
        )
        attempt_bid_after_auction_ends(
            self,
            self.cursor,
            auction_end,
            auction_id,
            user_id
        )

    def test_all_auctions_maintain_accurate_number_of_bids(self):
        add_trigger(self.trigger_dir, self.cursor, 6)
        auction_id, bidder_id = self.create_new_bidder_and_auction()

        make_new_bid_for_ten_dollars(self.cursor, auction_id, bidder_id)
        self.assertEqual(
            1,
            self.cursor.execute(
                "select number_of_bids "
                "from auction "
                f"where id={auction_id}"
            ).fetchone()[0]
        )

    def test_new_bid_price_must_exceed_current_highest_bid(self):
        add_trigger(self.trigger_dir, self.cursor, 7)
        auction_id, bidder_id = self.create_new_bidder_and_auction()
        make_new_bid_for_ten_dollars(self.cursor, auction_id, bidder_id)
        self.verify_deny_bid_with_price_lower_than_current_high(auction_id, bidder_id)
        self.verify_allow_bid_insertion_with_higher_price(auction_id, bidder_id)

    def test_new_bids_occur_at_controlled_time(self):
        add_trigger(self.trigger_dir, self.cursor, 8)
        auction = self.cursor.execute(
            "select id, start, end, seller_id, highest_bid "
            "from auction "
            "where end > datetime(start, '+2 hours')"
            "limit 1;"
        ).fetchone()
        auction_id = auction[0]
        start = auction[1]
        seller_id = auction[3]
        bid_price = 1 if auction[4] is None else float(auction[4]) + 1

        bidder_id = self.cursor.execute(
            f"select id "
            f"from user "
            f"where id !='{seller_id}' "
            f"limit 1;"
        ).fetchone()[0]

        pseudo_now = add_hours_to_datestring(start, 1)
        self.cursor.execute(
            "update pseudo_time "
            f"set now='{pseudo_now}';"
        )

        self.cursor.execute(
            f"insert into bid "
            f"values ("
            f"{auction_id}, "
            f"'{bidder_id}', "
            f"null, "
            f"{bid_price}"
            f");"
        )

        bid_time = self.cursor.execute(
            f"select time "
            f"from bid "
            f"where auction_id={auction_id} "
            f"and user_id='{bidder_id}'"
            f"and amount={bid_price} "
            f"limit 1;"
        ).fetchone()[0]

        self.assertEqual(
            pseudo_now,
            bid_time
        )

    def test_pseudo_time_only_moves_forward(self):
        add_trigger(self.trigger_dir, self.cursor, 9)

        try:
            self.cursor.execute(
                f"insert into pseudo_time "
                f"values ('{now()}');"
            )
        except sqlite3.IntegrityError as e:
            self.assertTrue(
                False,
                "Database failed to accept forward modification of pseudo time."
            )

        try:
            self.cursor.execute(
                f"insert into pseudo_time "
                f"values ('{now(-1)}');"
            )
        except sqlite3.IntegrityError as e:
            self.assertEquals(
                "Users may only move the pseudo time forward.",
                str(e)
            )

    def create_new_bidder_and_auction(self):
        seller_id = "testuser1234567890"
        bidder_id = "987654321testuser"
        add_new_users(self.cursor, bidder_id, seller_id)
        create_new_auction(self.cursor, seller_id)
        auction_id = fetch_last_row_added(self.cursor)
        return auction_id, bidder_id

    def verify_allow_bid_insertion_with_higher_price(self, auction_id, bidder_id):
        try:
            self.cursor.execute(
                "insert or replace into bid "
                f"values "
                f"("
                f"{auction_id}, "
                f"'{bidder_id}', "
                f"'{now(1)}', "
                f"40.00"
                f")"
            )
        except sqlite3.IntegrityError as e:
            self.assertTrue(
                False,
                f"Database failed to allow valid bid that exceeded current highest. Threw error:\n{e}"
            )

    def verify_deny_bid_with_price_lower_than_current_high(self, auction_id, bidder_id):
        try:
            self.cursor.execute(
                "insert into bid "
                f"values ({auction_id}, '{bidder_id}','{now()}', 3.50);"
            )
            self.assertTrue(
                False,
                "Database failed to deny low bid."
            )
        except sqlite3.IntegrityError as e:
            self.assertEqual(
                "New bids must exceed the current highest bid.",
                str(e)
            )


if __name__ == '__main__':
    if len(sys.argv) > 1:
        TestTriggers.real_database = sys.argv.pop()
    unittest.main()
