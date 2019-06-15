from JSONParser import *
from Writer import *


def convert_json_to_dat(filepaths, dat_filepath, top_key, child_keys, parent_key=''):
    if parent_key == '':
        ingest_single_value_from_files(
            filepaths,
            dat_filepath,
            top_key,
            child_keys
        )
    else:
        ingest_related_values_from_files(
            filepaths,
            dat_filepath,
            top_key,
            child_keys,
            parent_key
        )


def ingest_single_value_from_files(filepaths, dat_filepath, top_key, key):
    values = []
    for filepath in filepaths:
        values = values_from_json_file(
            values,
            list_of_objects_from_json_file(
                filepath,
                top_key
            ),
            key
        )
    print(f'max length of {key}: {max_length(values)}')
    write_values_to_dat(
        values,
        dat_filepath
    )


def ingest_related_values_from_files(filepaths, dat_filepath, top_key, child_keys, parent_key):
    if type(child_keys) == str:
        values = set()
    else:
        values = dict()

    max_len = 0
    for filepath in filepaths:
        if type(child_keys) == str:
            values = values_with_single_relationship(
                values,
                list_of_objects_from_json_file(filepath, top_key),
                child_keys,
                parent_key
            )
        else:
            values = values_with_many_collocated_relationships(
                values,
                list_of_objects_from_json_file(filepath, top_key),
                child_keys,
                parent_key
            )
    for value in values:
        if len(value[0]) > max_len:
            max_len = len(value[0])
    if type(child_keys) == str:
        print(f'max length of {child_keys}: {max_length(values)}')
    write_values_to_dat(values, dat_filepath)


def ingest_related_dislocated_values_from_files(
        filepaths,
        dat_filepath,
        top_key,
        child_keys,
        parent_key,
        disjointed_children_keys,
        parent_unique_id

):
    values = dict()
    for filepath in filepaths:
        values = values_with_dislocated_relationships(
            values,
            list_of_objects_from_json_file(
                filepath,
                top_key
            ),
            child_keys,
            parent_key,
            disjointed_children_keys,
            parent_unique_id
        )
    for key in values:
        if type(values[key]) == str:
            print(f'max length of {key}: {max_length(values)}')
    print(f'max length of {parent_unique_id}: {max_length(list(values.keys()))}')
    write_values_to_dat(values, dat_filepath)


def ingest_bids(
        filepaths,
        dat_filepath
):
    bids = dict()
    for filepath in filepaths:
        bids = get_bids(
            bids,
            list_of_objects_from_json_file(
                filepath,
                'Items'
            )
        )
        write_bids_to_dat(bids, dat_filepath)


def ingest_auctions(
        filepaths,
        dat_filepath
):
    auctions = dict()
    for filepath in filepaths:
        auctions = get_auctions(
            auctions,
            list_of_objects_from_json_file(
                filepath,
                'Items'
            )
        )
    write_values_to_dat(
        auctions,
        dat_filepath,
        ['Buy_Price', 'First_Bid'],
        ['Started', 'Ends']
    )


def join_auction_category(
        filepaths,
        dat_filepath
):
    joins = set()
    for filepath in filepaths:
        joins = join(
            joins,
            list_of_objects_from_json_file(
                filepath,
                'Items'
            )
        )
    write_values_to_dat(
        joins,
        dat_filepath
    )


def ingest_bidders(
        filepaths,
        dat_filepath
):
    bids = dict()
    for filepath in filepaths:
        bids = get_bids(
            bids,
            list_of_objects_from_json_file(
                filepath,
                'Items'
            )
        )
    bidders = get_bidders(bids)
    write_values_to_dat(
        bidders,
        dat_filepath
    )


def ingest_users(
        filepaths,
        dat_filepath
):
    bids = dict()
    for filepath in filepaths:
        bids = get_bids(
            bids,
            list_of_objects_from_json_file(
                filepath,
                'Items'
            )
        )
    bidders = get_bidders(bids)

    sellers = dict()
    for filepath in filepaths:
        sellers = values_with_dislocated_relationships(
            sellers,
            list_of_objects_from_json_file(
                filepath,
                'Items'
            ),
            ['Rating'],
            'Seller',
            ['Location', 'Country'],
            'UserID'
        )

    users = {**bidders, **sellers}

    write_values_to_dat(
        users,
        dat_filepath
    )


def max_length(values, current_max=0):
    max_len = 0
    if type(values) == str:
        max_len = len(values) if len(values) > current_max else current_max
    elif type(values) == list:
        for value in values:
            if len(value) > max_len:
                max_len = len(value)
    elif type(values) == set:
        for value in values:
            if len(value[0]) > max_len:
                max_len = len(value[0])
    elif type(values) == dict:
        for key in values:
            if len(values[key]) > max_len:
                max_len = len(values[key])
    return max_len
