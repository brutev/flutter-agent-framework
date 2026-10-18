# Online Python compiler (interpreter)
# Write and run Python online using this editor.

def twoSum(numbers, target):
    left = 0
    right = len(numbers) - 1



    while left < right:
      current_sum  = numbers[left]+ numbers[right]

      if current_sum == target:
        return [numbers[left+1],numbers[right+1]]
      elif current_sum > target:
        right -=1
      else:
        left += 1

    return []