import blocks


def test_split_block_segments_preserves_inline_direction_and_exclamations() -> None:
    text = "(_who has picked himself up and is sneaking past Ferrovius on his left, sneers derisively_)!!"
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_who has picked himself up and is sneaking past Ferrovius on his left, sneers derisively_)",
        "!!",
    ]


def test_split_block_segments_trivial_punctuation_stays_with_direction() -> None:
    text = "(_who has picked himself up and is sneaking past Ferrovius on his left, sneers derisively_)."
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_who has picked himself up and is sneaking past Ferrovius on his left, sneers derisively_)",
    ]
