from errant import Errant

annotate = Errant()
original = 'This widespread propaganda benefits only to the companys.'
corrected = 'This widespread publicity only benefits their companies.'
orignal_tokens = annotate.parse(original)
corrected_tokens = annotate.parse(corrected)
edits = annotate.get_typed_edits(orignal_tokens, corrected_tokens)
print(edits)