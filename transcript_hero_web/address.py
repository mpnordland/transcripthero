import pycountry


def _pair_key_func(pair):
    return pair[0]


def get_country_choices():
    country_list = []

    for country in pycountry.countries:
        country_list.append((country.name, country.name))

    return sorted(country_list, key=_pair_key_func)


def get_state_choices():
    state_choices = []
    states = pycountry.subdivisions.get(country_code='US')
    for state in states:
        state_choices.append((state.name, state.name))
    return sorted(state_choices, key=_pair_key_func)
