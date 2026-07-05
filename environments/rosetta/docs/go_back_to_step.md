`go_back_to_step` allows you to reset the environment state to a previous step in the trajectory. This action resets the environment to the observed state at the end of the specified step (i.e., after the action in the step is performed). This action is useful to retry actions or explore different paths.

**`step` argument:**

The number of the step to revert to, starting from 0, which is the initial state of the environment.

---

For example:

<action tag="run">
<name>go_back_to_step</name>
<step>step_number</step>
</action>

resets the environment to the observed state of the environment after the action in step `step_number` was performed.
