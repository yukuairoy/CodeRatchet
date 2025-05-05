# Ratchet Tests

Tests that lazily enforce a requirement across the entire repo. 

## Enforcement

For daily use and enforcement, we include a test `test_all_ratchets` inside `test_all_ratchets.py` that will verify none of the ratchets have been loosened. To run:

From standalone/research:
```bash
python -m research.ratchets.test_all_ratchets test
```

If this test fails for you, it most likely means that you have added a new use of a banned function, import or pattern. They run as part of the core fast tests build.

### How can I figure out what recent changes have broken ratchets?
Run the following from this folder:
```bash
python -m research.ratchets.get_most_recently_broken_ratchets
```
This python program will print the 10 most-recently-committed (or uncommitted) lines that break our ratchet rules. If none of the ratchet rules have more than their allowed counts, it will run for all rules, which may be a bit slower.

### These files shouldn't be measured. What should I do?
By the toplevel `ratchet_excluded.txt`, ratchets don't run on a small selection of folders such as `notebook/` or `quarantine/` folders. If code quality doesn't matter for a file or folder, it can be added to the exclude list. `ratchet_excluded.txt` files follow the gitignore format and semantics. They can appear anywhere within the repo and pattern match relative to their location.  

## Updating counts
On a periodic basis, we ought to update our counts so that our ratchets can actually make progress. To do so is simple. Run the following:
```bash
python -m research.ratchets.test_all_ratchets update
```
This should overwrite ratchet_values.json with the current counts. Inspect it manually to verify that no counts have increased. Then you can commit and merge the new counts.

## Adding new ratchet tests

To add a new test, create a new ratchet_tests entry in `ratchet_rules.py`. Each entry requires a unique name and a regex to search for. It's also highly encouraged to include some examples to test the regex. An example entry might look like:

```python
RatchetTest(
    name="pytorch_lightning",
    regex=re.compile(r"import pytorch_lightning|from pytorch_lightning"),
    match_examples=[
        "from pytorch_lightning import LightningModule",
        "import pytorch_lightning as pl",
    ],
    non_match_examples=[
        "from this_package import the_thing",
        "import super_lightning as sl"
    ]
)
```

To validate that the match_examples are working correctly,
```bash
python -m research.ratchets.test_all_ratchets check_examples
```

Immediately after adding such an entry, the `test_all_ratchets` test should fail - we default to 0 allowed occurrences. Update counts to get the initial count saved and bring tests to passing again.

## TODO:
We might consider adding a periodic job/task or a pre-commit hook to update the counts of our ratchets. 

Also, this probably ought to live in its own toplevel folder or in a toplevel codebase-wide-tests sort of folder. It will remain here for now so that these tests are run as part of CI rather than not at all.
