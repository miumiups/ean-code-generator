from configparser import ConfigParser


class Pointer:

    def __init__(self, config_path):
        # Access to config
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")

        self.start_changelog_id = config['CODES']['START_CHANGELOG_ID']
        self.ean_number_start = int(config['EAN']['EAN_NUMBER_START'])

        self.saved_changelog_id = None

    def get_ean(self, pointer_path):
        # Extract the latest used values from POINTER.txt file
        with open(pointer_path) as file:
            contents = file.readlines()[1].strip().split(",")
        self.saved_changelog_id = contents[0]
        saved_ean = contents[1]

        # At the start, use numbers from config file when the values in pointer.txt are 'none'
        if saved_ean == 'none':
            ean = self.ean_number_start - 1  # -1 cuz we'll +1 before we use it later
        else:
            ean = int(saved_ean)

        return ean

    def get_changelog_id(self):
        if self.saved_changelog_id == 'none':
            changelog_id = self.start_changelog_id
        else:
            changelog_id = self.saved_changelog_id

        return changelog_id

    def write(self, changelog_id, ean):
        with open("POINTER.txt", mode="w") as file:
            updated_contents = f"changelog_id,ean\n{changelog_id},{ean}"
            file.write(updated_contents)


