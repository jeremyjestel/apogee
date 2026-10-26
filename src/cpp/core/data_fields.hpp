#pragma once

#include <tuple>

namespace apogee
{
	// Data descriptions belong to their owning types; consumers only read accessors.
	template <typename Accessor> struct DataField
	{
		const char *key;
		Accessor accessor;
		const char *name;
		const char *unit;
		const char *frame;
	};

	template <typename Accessor>
	constexpr DataField<Accessor> data_field(const char *key,
		Accessor accessor,
		const char *name,
		const char *unit = "",
		const char *frame = "")
	{
		return { key, accessor, name, unit, frame };
	}

	// Share editable parameter metadata without restricting data to editable inputs.
	template <typename ParameterTuple> constexpr auto data_fields(const ParameterTuple &parameters)
	{
		return std::apply(
			[](const auto &...field)
			{
				return std::tuple{ data_field(field.key, field.member, field.name, field.unit)... };
			},
			parameters);
	}

} // namespace apogee
