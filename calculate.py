import json,sys
from dataclasses import dataclass

@dataclass
class Rating:
    poor: int
    below_average: int
    average: int
    good: int
    excellent: int

    @classmethod
    def zero(cls):
        return cls(0, 0, 0, 0, 0)

    @classmethod
    def from_dict(cls, data):
        return cls(
            poor = int(data['poor']),
            below_average = int(data['below_average']),
            average = int(data['average']),
            good = int(data['good']),
            excellent = int(data['excellent'])
        )

    def add(self, other):
        return Rating(
            poor=self.poor + other.poor,
            below_average=self.below_average + other.below_average,
            average=self.average + other.average,
            good = self.good + other.good,
            excellent = self.excellent + other.excellent
        )

    def get_top1(self):
        return 100 * self.excellent / self.get_count()

    def get_top2(self):
        return 100* (self.excellent + self.good) / self.get_count()

    def to_list(self):
        return [self.poor, self.below_average, self.average, self.good, self.excellent]

    def get_count(self):
        return self.poor + self.below_average + self.average + self.good + self.excellent

    def get_mean(self):
        return (1 * self.poor + 2 * self.below_average + 3 * self.average + 4 * self.good + 5 * self.excellent) / self.get_count()

def main():
    filename = sys.argv[1]
    print(filename)
    with open(filename) as fp:
        data = json.load(fp)
    excellents = 0
    goods = 0
    count = 0
    ratings = []
    total = Rating.zero()
    for line in data:
        rating = Rating.from_dict(line)
        total = total.add(rating)
        ratings.append(rating)
        excellents += rating.excellent
        goods += rating.good
        count += int(line['count'])
    top1 = total.excellent / count
    top2 = (total.excellent + total.good) / count
    t = total
    print(f"Top1: {t.get_top1():.2f}% Top2: {t.get_top2():.2f}% Mean: {t.get_mean():.3f}")


if __name__ == '__main__':
    main()
