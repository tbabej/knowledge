import vim


NEOVIM = (vim.eval('has("nvim")') == "1")


def decode_bytes(var):
    """
    Data structures obtained from vim under python3 will return bytestrings.
    Neovim under python3 will return str.
    Make sure we can handle that.
    """

    if NEOVIM:
        return var

    if isinstance(var, bytes):
        return var.decode()

    if isinstance(var, list):
        return list([decode_bytes(element) for element in var])

    if isinstance(var, dict) or 'vim.dictionary' in str(type(var)):
        return  {
            decode_bytes(key): decode_bytes(value)
            for key, value in var.items()
        }

    return var


def get_var(name, default=None, vars_obj=None):
    """
    Provide a layer for getting a variable value out of vim, consistent over
    vim+py2/vim+py3/neovim combinations.

    Params:
        default - default value, returned when variable is not found
        vars - used vars object, defaults to vim.vars
    """

    vars_obj = vars_obj or vim.vars
    value = vars_obj.get(name)

    if value is None:
        return default
    else:
        return decode_bytes(value)


def close_fold(line):
    # Line number needs to be normalized for vim
    line = line + 1

    # Check if line is already closed
    fold_closed = (vim.eval("foldclosed({0})".format(line)) != '-1')

    if not fold_closed:
        # Do not sprinkle errors if closing the fold fails for whatever reason
        try:
            vim.command(f"{line}foldclose")
        except Exception:
            pass


def decode_bytes(var):
    """
    Data structures obtained from vim under python3 will return bytestrings.
    Make sure we can handle that.
    """

    if isinstance(var, bytes):
        return var.decode()
    if isinstance(var, list) or 'vim.list' in str(type(var)):
        return list([decode_bytes(element) for element in var])

    if isinstance(var, dict) or 'vim.dictionary' in str(type(var)):
        return  {
            decode_bytes(key): decode_bytes(value)
            for key, value in var.items()
        }

    return var


def get_absolute_filepath():
    return vim.eval('expand("%:p")')


def get_current_line_number():
    row, column = vim.current.window.cursor
    return row - 1


def get_current_column_number():
    row, column = vim.current.window.cursor
    return column
