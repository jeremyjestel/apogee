#include "logging/logging.hpp"

#include <cmath>
#include <functional>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <unordered_set>

namespace apogee
{
	namespace
	{
		constexpr double missing = std::numeric_limits<double>::quiet_NaN();

		template <typename T> struct IsVector : std::false_type {};
		template <typename T, typename A> struct IsVector<std::vector<T, A>> : std::true_type {};
		template <typename T> struct IsOptional : std::false_type {};
		template <typename T> struct IsOptional<std::optional<T>> : std::true_type {};

		template <typename T> constexpr bool is_component()
		{
			if constexpr (requires { T::data_fields(); }) return true;
			else if constexpr (IsOptional<T>::value) return is_component<typename T::value_type>();
			else if constexpr (IsVector<T>::value) return is_component<typename T::value_type>();
			else return false;
		}

		std::string joined(const std::string &prefix, const std::string &part)
		{
			return prefix.empty() ? part : prefix + "/" + part;
		}

		std::string component_key(const std::string &name)
		{
			constexpr char hex[] = "0123456789ABCDEF";
			std::string key = "name:";
			for (unsigned char c : name)
			{
				if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
					(c >= '0' && c <= '9') || c == '_' || c == '-') key += c;
				else { key += '%'; key += hex[c >> 4]; key += hex[c & 15]; }
			}
			return key;
		}
	}

	std::string Logger::identity(const Field &field)
	{
		return std::to_string(field.entity_id) + "\x1f" + field.system + "\x1f" + field.key;
	}

	std::vector<Logger::Sample> Logger::capture(const std::vector<Entity> &entities)
	{
		std::vector<Sample> samples;
		std::unordered_set<int> ids;
		std::unordered_set<std::string> fields;
		auto emit = [&](Field field, Value value)
		{
			if (!fields.insert(identity(field)).second)
				throw std::invalid_argument("Duplicate logged field: " + field.system + "/" + field.key);
			samples.push_back({ std::move(field), std::move(value) });
		};

		auto walk = [&]<typename T>(auto &&self, const T &value, Field field, bool root = false) -> void
		{
			if constexpr (IsOptional<T>::value)
			{
				if (value) self(self, *value, std::move(field));
			}
			else if constexpr (requires { T::data_fields(); })
			{
				std::apply([&](const auto &...description)
				{
					auto visit = [&](const auto &description)
					{
						const auto &member = std::invoke(description.accessor, value);
						using Member = std::remove_cvref_t<decltype(member)>;
						Field child = field;
						child.name = description.name;
						child.unit = description.unit;
						if (*description.frame) child.frame = description.frame;
						if (root && is_component<Member>())
						{
							child.system = description.key;
							child.key.clear();
						}
						else
						{
							child.key = joined(field.key, description.key);
							if constexpr (is_component<Member>())
								child.group = joined(field.group, description.name);
						}
						self(self, member, std::move(child));
					};
					(visit(description), ...);
				}, T::data_fields());
			}
			else if constexpr (std::is_arithmetic_v<T> || std::is_enum_v<T>)
				emit(std::move(field), static_cast<double>(value));
			else if constexpr (std::is_same_v<T, std::string>)
				emit(std::move(field), value);
			else if constexpr (std::is_same_v<T, Vec3>)
				emit(std::move(field), value);
			else if constexpr (requires { typename T::Scalar; value.rows(); value.cols(); })
			{
				ArraySample array{ .rows = static_cast<std::size_t>(value.rows()),
					.columns = static_cast<std::size_t>(value.cols()) };
				array.values.reserve(array.rows * array.columns);
				for (Index row = 0; row < value.rows(); ++row)
					for (Index column = 0; column < value.cols(); ++column)
						array.values.emplace_back(value(row, column));
				emit(std::move(field), std::move(array));
			}
			else if constexpr (IsVector<T>::value)
			{
				using Item = typename T::value_type;
				if constexpr (std::is_same_v<Item, Entity> || std::is_arithmetic_v<Item> ||
					std::is_enum_v<Item> || std::is_same_v<Item, Complex>)
				{
					ArraySample array{ .rows = value.size(), .columns = 1 };
					array.values.reserve(value.size());
					for (const auto &item : value)
					{
						if constexpr (std::is_same_v<Item, Entity>) array.values.emplace_back(item.id);
						else if constexpr (std::is_enum_v<Item>) array.values.emplace_back(static_cast<double>(item));
						else array.values.emplace_back(item);
					}
					emit(std::move(field), std::move(array));
				}
				else
				{
					Field count = field;
					count.key = joined(field.key, "count");
					count.name += " count";
					emit(std::move(count), static_cast<double>(value.size()));
					std::unordered_set<std::string> keys;
					for (std::size_t i = 0; i < value.size(); ++i)
					{
						std::string key = "index:" + std::to_string(i);
						std::string name = field.name + " " + std::to_string(i);
						if constexpr (requires { value[i].name; })
							if (!value[i].name.empty()) { key = component_key(value[i].name); name = value[i].name; }
						if (!keys.insert(key).second)
							throw std::invalid_argument("Duplicate component name: " + name);
						Field child = field;
						child.key = joined(field.key, key);
						child.group = joined(field.group, name);
						self(self, value[i], std::move(child));
					}
				}
			}
			else static_assert(sizeof(T) == 0, "Describe this data type before logging it.");
		};

		for (const Entity &entity : entities)
		{
			if (entity.id == 0 || !ids.insert(entity.id).second)
				throw std::invalid_argument("Logged entities require unique nonzero IDs.");
			walk(walk, entity, Field{ .entity_id = entity.id, .system = "entity" }, true);
		}
		return samples;
	}

	Logger::Logger(const std::vector<Entity> &entities, Result &result) : result_(result)
	{
		const auto samples = capture(entities);
		for (const Axis &axis : result.axes)
			if (axis.key == "simulation_time")
				throw std::invalid_argument("Result already contains a simulation timeline.");
		simulation_time_axis_ = result.axes.size();
		register_entities(entities);
		result.axes.push_back(Axis{
			.key = "simulation_time", .name = "Simulation Time", .unit = "s", .kind = "time" });
		register_fields(samples);
	}

	void Logger::register_entities(const std::vector<Entity> &entities)
	{
		std::unordered_set<std::string> keys;
		for (const EntityDescriptor &entity : result_.entities) keys.insert(entity.key);
		auto entity_key = [](const Entity &entity)
		{
			return entity.key.empty() ? "entity_" + std::to_string(entity.id) : entity.key;
		};
		// Validate the complete snapshot before registering any newly appearing entity.
		for (const Entity &entity : entities)
		{
			if (entities_.contains(entity.id)) continue;
			const std::string key = entity_key(entity);
			if (!keys.insert(key).second)
				throw std::invalid_argument("Duplicate entity key: " + key);
		}
		for (const Entity &entity : entities)
		{
			if (entities_.contains(entity.id)) continue;
			entities_.emplace(entity.id, result_.entities.size());
			result_.entities.push_back(EntityDescriptor{ .id = entity.id, .key = entity_key(entity),
				.display_name = entity.display_name, .type = entity.type, .team = entity.team });
		}
	}

	void Logger::register_fields(const std::vector<Sample> &samples)
	{
		const std::size_t count = result_.axes[simulation_time_axis_].values.size();
		for (const Sample &sample : samples)
		{
			const Field &f = sample.field;
			const std::string key = identity(f);
			if (series_.contains(key))
			{
				if (series_.at(key).kind != sample.value.index())
					throw std::invalid_argument("Logged field changed type: " + f.key);
				continue;
			}
			const Presentation presentation{ .group = f.group };
			Series series{ .kind = sample.value.index() };
			switch (series.kind)
			{
			case 0:
				series.index = result_.scalars.size();
				result_.scalars.push_back(ScalarSeries{ .entity_id = f.entity_id, .system = f.system,
					.key = f.key, .name = f.name, .unit = f.unit, .axis_key = "simulation_time",
					.values = std::vector<double>(count, missing), .presentation = presentation });
				break;
			case 1:
				series.index = result_.vectors.size();
				result_.vectors.push_back(VectorSeries3{ .entity_id = f.entity_id, .system = f.system,
					.key = f.key, .name = f.name, .unit = f.unit, .frame = f.frame,
					.axis_key = "simulation_time", .values = std::vector<Vec3>(count, Vec3::Constant(missing)),
					.presentation = presentation });
				break;
			case 2:
				series.index = result_.texts.size();
				result_.texts.push_back(TextSeries{ .entity_id = f.entity_id, .system = f.system,
					.key = f.key, .name = f.name, .unit = f.unit, .axis_key = "simulation_time",
					.values = std::vector<std::optional<std::string>>(count), .presentation = presentation });
				break;
			case 3:
				series.index = result_.arrays.size();
				result_.arrays.push_back(ArraySeries{ .entity_id = f.entity_id, .system = f.system,
					.key = f.key, .name = f.name, .unit = f.unit, .axis_key = "simulation_time",
					.values = std::vector<std::optional<ArraySample>>(count), .presentation = presentation });
				break;
			}
			series_.emplace(key, series);
		}
	}

	void Logger::log(const std::vector<Entity> &entities, double time_s)
	{
		auto &times = result_.axes[simulation_time_axis_].values;
		if (!std::isfinite(time_s) || (!times.empty() && time_s <= times.back()))
			throw std::invalid_argument("Logging times must be finite and strictly increasing.");
		auto samples = capture(entities);
		register_entities(entities);
		register_fields(samples);
		times.push_back(time_s);
		for (const auto &[key, series] : series_)
		{
			switch (series.kind)
			{
			case 0: result_.scalars[series.index].values.push_back(missing); break;
			case 1: result_.vectors[series.index].values.push_back(Vec3::Constant(missing)); break;
			case 2: result_.texts[series.index].values.push_back(std::nullopt); break;
			case 3: result_.arrays[series.index].values.push_back(std::nullopt); break;
			}
		}
		for (Sample &sample : samples)
		{
			const Series series = series_.at(identity(sample.field));
			switch (series.kind)
			{
			case 0: result_.scalars[series.index].values.back() = std::get<double>(sample.value); break;
			case 1: result_.vectors[series.index].values.back() = std::get<Vec3>(sample.value); break;
			case 2: result_.texts[series.index].values.back() = std::move(std::get<std::string>(sample.value)); break;
			case 3: result_.arrays[series.index].values.back() = std::move(std::get<ArraySample>(sample.value)); break;
			}
		}
	}

} // namespace apogee
