import jionlp as jio

text = "北京市 北京市 北京 八角北路53号杨庄中学"
print(f"Testing text: {text}")
try:
    res = jio.parse_location(text)
    print(f"Result: {res}")
except Exception as e:
    print(f"Error: {e}")

text2 = "北京市 北京市 海淀区 北京市西三环中路19号海军大院西门"
print(f"Testing text: {text2}")
try:
    res = jio.parse_location(text2)
    print(f"Result: {res}")
except Exception as e:
    print(f"Error: {e}")
