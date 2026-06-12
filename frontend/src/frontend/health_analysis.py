import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell
def _():
    """
    Prints "hello world!" to standard output.
    """
    print("hello world!")
    return


if __name__ == "__main__":
    app.run()
