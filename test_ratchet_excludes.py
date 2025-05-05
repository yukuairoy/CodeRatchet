# We have a ratchet test that looks for this string but since we're excluded by ratchet_excludes.txt it shouldn't
# find this occurrence
def a_long_string_that_shouldnt_appear_anywhere_naturally() -> None:
    return
