import pandas as pd

def to_sub(file):
    file_pointer = open(file)
    r = file_pointer.read()
    read_file = r.split('\n')
    file_pointer.close()
    #print('len_read_file:',len(read_file))
    sub_line = []
    groups = []
    # print(len(read_file))
    # taking one group of data and putting it all on one line
    for line in read_file:
        if line != '': #'/r/ as a bytestream thing
            sub_line.append(line)
        else:
            if sub_line != []:
                groups.append(sub_line)
            sub_line = []

    line = []
    timestart = []
    timeend = []

    for group in groups:
        line.append((" ".join(group[2:])))

        # turn time into seconds
        unformat_time = group[1]
        left, right = unformat_time.split('-->')
        left = left.replace(' ', '').split(':')
        right = right.replace(' ', '').split(':')
        left_sum = int(left[0]) * 60 * 60 * 1000 + int(left[1]) * 60 * 1000 + int(left[2].replace(',', '')) + 500
        right_sum = int(right[0]) * 60 * 60 * 1000 + int(right[1]) * 60 * 1000 + int(right[2].replace(',', '')) + 500
        timestart.append(left_sum)
        timeend.append(right_sum)
        # print(left_sum, right_sum)
        # print(left,right)

    sub_df = pd.DataFrame({'TimeStart': timestart, 'TimeEnd': timeend, 'Text': line})

    return sub_df