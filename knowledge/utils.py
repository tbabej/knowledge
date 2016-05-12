import vim

def string_to_args(line):
    output = []
    escape_global_chars = ('"', "'")
    line = line.strip()

    current_escape = None
    current_part = ''
    local_escape_pos = None

    for i in range(len(line)):
        char = line[i]
        ignored = False
        process_next_part = False

        # If previous char was \, add to current part no matter what
        if local_escape_pos == i - 1:
            local_escape_pos = None
        # If current char is \, use it as escape mark and ignore it
        elif char == '\\':
            local_escape_pos = i
            ignored = True
        # If current char is ' or ", open or close an escaped seq
        elif char in escape_global_chars:
            # First test if we're finishing an escaped sequence
            if current_escape == char:
                current_escape = None
                ignored = True
            # Do we have ' inside "" or " inside ''?
            elif current_escape is not None:
                pass
            # Opening ' or "
            else:
                current_escape = char
                ignored = True
        elif current_escape is not None:
            pass
        elif char == ' ':
            ignored = True
            process_next_part = True

        if not ignored:
            current_part += char

        if process_next_part and current_part:
            output.append(current_part)
            current_part = ''

    if current_part:
        output.append(current_part)

    return output

def string_to_kwargs(line):
    args = string_to_args(line)
    return args_to_kwargs(args)

def args_to_kwargs(args):
    output = dict()

    for arg in args:
        # If the argument contains :, then it's a key/value pair
        if ':' in arg and '::' not in arg:
            key, value = arg.split(':', 1)
            # Ignore anything which is not one-word string of alpha chars
            if key.isalpha():
                output[key] = value if value is not "" else None
        # Tag addition
        elif arg.startswith('+'):
            value = arg[1:]
            output.setdefault('tags', []).append(value)
        else:
            output['deck'] = arg

    return output

def close_fold(line):
    # Line number needs to be normalized for vim
    line = line + 1

    # Check if line is already closed
    fold_closed = (vim.eval("foldclosed({0})".format(line)) != '-1')

    if not fold_closed:
        vim.command("{0}foldclose".format(line))
